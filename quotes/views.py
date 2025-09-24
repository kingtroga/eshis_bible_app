from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q, Prefetch
from django.contrib import messages
from django.core.cache import cache
from .models import Book, Quote, CachedVerse, SearchCache
from .bible_api import BibleAPIClient
from .tasks import verse_cache
import random
import time

def get_chapter_verse_from_quote(quote):
    """Parse chapter:verse format into chapter and list of verses"""
    parts = quote.split(":")
    chapter = parts[0]
    verse_parts = parts[1].split(",")
    
    verses = []
    for verse_part in verse_parts:
        verse_part = verse_part.strip()
        if "-" in verse_part:
            start, end = verse_part.split("-")
            verses.extend(range(int(start), int(end) + 1))
        else:
            verses.append(int(verse_part))
    
    return chapter, verses

def home(request):
    """Home page with Jesus quotes and search"""
    client = BibleAPIClient()
    
    # Get filter parameters
    book_filter = request.GET.get('book', '')
    search_query = request.GET.get('q', '').strip()
    view_mode = request.GET.get('mode', 'quotes')
    
    context = {
        'books': Book.objects.all(),
        'current_book': book_filter,
        'search_query': search_query,
        'view_mode': view_mode
    }
    
    if search_query and view_mode == 'search':
        # API.Bible search
        try:
            page = int(request.GET.get('page', 1))
            limit = 20
            offset = (page - 1) * limit
            
            search_results = client.search_verses(
                query=search_query,
                limit=limit,
                offset=offset,
                sort='canonical'
            )
            
            verses = search_results.get('verses', [])
            total = search_results.get('total', 0)
            
            has_next = offset + limit < total
            has_previous = offset > 0
            
            context.update({
                'search_results': verses,
                'search_total': total,
                'has_next': has_next,
                'has_previous': has_previous,
                'current_page': page,
                'next_page': page + 1 if has_next else None,
                'previous_page': page - 1 if has_previous else None,
            })
            
        except Exception as e:
            messages.error(request, f"Search error: {e}")
            context['search_results'] = []
    
    else:
        # Show Jesus quotes with smart caching
        quotes = Quote.objects.select_related('book').prefetch_related(
            Prefetch(
                'cached_verses',
                queryset=CachedVerse.objects.order_by('verse_number')
            )
        )
        
        if book_filter:
            quotes = quotes.filter(book__name=book_filter)
        
        if search_query:
            quotes = quotes.filter(
                Q(cached_verses__text__icontains=search_query) |
                Q(book__name__icontains=search_query) |
                Q(reference__icontains=search_query)
            ).distinct()
        
        paginator = Paginator(quotes, 20)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        # Cache some quotes on-demand (only occasionally)
        cache_key = 'last_cache_attempt'
        last_cache = cache.get(cache_key, 0)
        current_time = time.time()
        
        # Cache every 5 minutes at most, and only 20% of the time
        if (current_time - last_cache > 300) and random.random() < 0.2:
            try:
                verse_cache.cache_random_quotes(2)  # Cache 2 quotes
                cache.set(cache_key, current_time, 600)  # Remember for 10 minutes
            except:
                pass  # Ignore errors
        
        context.update({
            'page_obj': page_obj,
            'total_quotes': quotes.count()
        })
    
    return render(request, 'quotes/home.html', context)

def quote_detail(request, quote_id):
    """Detail view - cache this quote immediately"""
    quote = get_object_or_404(Quote, id=quote_id)
    
    # Cache this specific quote if not cached
    cached_verses = quote.cached_verses.all().order_by('verse_number')
    
    if not cached_verses.exists():
        try:
            verse_cache.cache_quote_immediately(quote)
            cached_verses = quote.cached_verses.all().order_by('verse_number')
        except Exception as e:
            messages.warning(request, "Loading verses, please refresh if needed.")
    
    # Build verses list
    verses = []
    for cached_verse in cached_verses:
        verses.append({
            'id': cached_verse.verse_id,
            'reference': cached_verse.reference,
            'text': cached_verse.text,
            'verse_number': cached_verse.verse_number,
            'cached': True
        })
    
    # If still no verses, try to load a few immediately
    if not verses:
        client = BibleAPIClient()
        verse_ids = quote.get_verse_ids_list()[:5]  # First 5 verses only
        
        for verse_id in verse_ids:
            try:
                verse_data = client.get_verse(verse_id)
                if verse_data:
                    verse_number = int(verse_id.split('.')[-1])
                    verses.append({
                        'id': verse_id,
                        'reference': verse_data['reference'],
                        'text': verse_data['text'],
                        'verse_number': verse_number,
                        'cached': False
                    })
            except:
                continue
    
    # Sort by verse number
    verses.sort(key=lambda x: x.get('verse_number', 0))
    
    context = {
        'quote': quote,
        'verses': verses
    }
    return render(request, 'quotes/detail.html', context)

def cache_verses_view(request):
    """AJAX endpoint to cache verses on demand"""
    if request.method == 'POST':
        try:
            cached_count = verse_cache.cache_random_quotes(3)
            return JsonResponse({
                'success': True,
                'cached_count': cached_count,
                'message': f'Cached {cached_count} quotes'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({'success': False, 'error': 'POST required'})

def api_quotes(request):
    """API endpoint for quotes data"""
    book_name = request.GET.get('book', '')
    search_query = request.GET.get('q', '')
    
    if search_query:
        client = BibleAPIClient()
        try:
            results = client.search_verses(search_query, limit=50)
            return JsonResponse(results)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    else:
        quotes = Quote.objects.select_related('book').prefetch_related('cached_verses')
        if book_name:
            quotes = quotes.filter(book__name=book_name)
        
        data = []
        for quote in quotes:
            verses_data = []
            for verse in quote.cached_verses.all().order_by('verse_number'):
                verses_data.append({
                    'verse': verse.verse_number,
                    'text': verse.text,
                    'reference': verse.reference
                })
            
            data.append({
                'book': quote.book.name,
                'reference': quote.reference,
                'verses': verses_data
            })
        
        return JsonResponse({'quotes': data})
