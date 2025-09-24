# ========== quotes/bible_api.py (HYBRID APPROACH) ==========
import requests
import json
import re
from django.conf import settings
from django.utils import timezone
from .models import Book, CachedVerse, SearchCache

class BibleAPIClient:
    def __init__(self):
        # API.Bible for search
        self.api_bible_key = settings.API_BIBLE_KEY
        self.api_bible_base_url = settings.API_BIBLE_BASE_URL
        self.bible_id = settings.BIBLE_ID
        self.api_bible_headers = {
            'api-key': self.api_bible_key,
            'Accept': 'application/json'
        }
        
        # Simple Bible API for verses
        self.simple_bible_base_url = "https://cdn.jsdelivr.net/gh/wldeh/bible-api/bibles"
        self.bible_version = "en-kjv"
    
    def get_books(self):
        """Get all books from API.Bible"""
        url = f"{self.api_bible_base_url}/bibles/{self.bible_id}/books"
        try:
            response = requests.get(url, headers=self.api_bible_headers, timeout=10)
            if response.status_code == 200:
                return response.json().get('data', [])
        except requests.RequestException as e:
            print(f"Error fetching books: {e}")
        return []
    
    def get_verse(self, verse_id):
        """Get a single verse using the simple Bible API (e.g., 'MAT.5.3')"""
        # Check cache first
        try:
            cached = CachedVerse.objects.get(verse_id=verse_id)
            return {
                'id': cached.verse_id,
                'reference': cached.reference,
                'text': cached.text,
                'cached': True
            }
        except CachedVerse.DoesNotExist:
            pass
        
        # Parse verse ID to get book, chapter, verse for simple API
        try:
            parts = verse_id.split('.')
            if len(parts) < 3:
                return None
                
            book_api_id = parts[0]
            chapter = parts[1]
            verse_number = parts[2]
            
            # Map API.Bible book IDs to simple API book names
            book_mapping = {
                'MAT': 'matthew', 'MRK': 'mark', 'LUK': 'luke', 'JHN': 'john',
                'ACT': 'acts', '1CO': '1-corinthians', '2CO': '2-corinthians',
                'REV': 'revelation'
            }
            
            book_name = book_mapping.get(book_api_id)
            if not book_name:
                print(f"Unknown book ID: {book_api_id}")
                return None
            
            # Fetch from simple Bible API
            url = f"{self.simple_bible_base_url}/{self.bible_version}/books/{book_name}/chapters/{chapter}/verses/{verse_number}.json"
            
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                verse_text = data.get('text', '').strip()
                
                if verse_text:
                    # Create reference string
                    book_display_name = book_name.replace('-', ' ').title()
                    reference = f"{book_display_name} {chapter}:{verse_number}"
                    
                    # Cache the verse
                    self._cache_verse_simple(verse_id, book_api_id, int(chapter), int(verse_number), verse_text, reference)
                    
                    return {
                        'id': verse_id,
                        'reference': reference,
                        'text': verse_text,
                        'cached': False
                    }
            else:
                print(f"Failed to fetch verse {verse_id}: HTTP {response.status_code}")
                
        except requests.RequestException as e:
            print(f"Error fetching verse {verse_id}: {e}")
        except ValueError as e:
            print(f"Error parsing verse ID {verse_id}: {e}")
        except Exception as e:
            print(f"Unexpected error fetching verse {verse_id}: {e}")
        
        return None
    
    def search_verses(self, query, limit=20, offset=0, sort='canonical'):
        """Search for verses using API.Bible search"""
        # Check cache first
        cache_key = f"{query}:{limit}:{offset}:{sort}"
        try:
            cached = SearchCache.objects.get(query=cache_key)
            if cached.is_fresh():
                return cached.get_results()
        except SearchCache.DoesNotExist:
            pass
        
        # Fetch from API.Bible
        url = f"{self.api_bible_base_url}/bibles/{self.bible_id}/search"
        params = {
            'query': query,
            'limit': limit,
            'offset': offset,
            'sort': sort
        }
        
        try:
            response = requests.get(url, headers=self.api_bible_headers, params=params, timeout=15)
            if response.status_code == 200:
                data = response.json().get('data', {})
                verses = data.get('verses', [])
                
                # Process and cache verses
                results = []
                for verse_data in verses:
                    # Clean the text from search results (API.Bible returns HTML)
                    raw_text = verse_data.get('text', '')
                    clean_text = self.clean_verse_text(raw_text)
                    
                    verse_info = {
                        'id': verse_data.get('id'),
                        'reference': verse_data.get('reference'),
                        'text': clean_text,
                        'book_id': verse_data.get('bookId'),
                        'chapter_id': verse_data.get('chapterId')
                    }
                    results.append(verse_info)
                    
                    # Cache individual verse from search (using API.Bible format)
                    self._cache_verse_from_search(verse_data, clean_text)
                
                # Cache search results
                SearchCache.objects.update_or_create(
                    query=cache_key,
                    defaults={
                        'results': json.dumps({
                            'verses': results,
                            'total': data.get('total', 0),
                            'query': data.get('query', query)
                        })
                    }
                )
                
                return {
                    'verses': results,
                    'total': data.get('total', 0),
                    'query': data.get('query', query)
                }
            else:
                print(f"API.Bible search failed: HTTP {response.status_code}")
                
        except requests.RequestException as e:
            print(f"Error searching: {e}")
        except Exception as e:
            print(f"Unexpected error searching: {e}")
        
        return {'verses': [], 'total': 0, 'query': query}
    
    def clean_verse_text(self, html_content):
        """Extract clean text from HTML content (for API.Bible search results)"""
        if not html_content:
            return ""
        
        # Remove HTML tags but keep the text
        clean_text = re.sub(r'<[^>]+>', '', html_content)
        
        # Remove verse numbers at the beginning (like "1" or "12")
        clean_text = re.sub(r'^\d+\s*', '', clean_text.strip())
        
        # Clean up extra whitespace
        clean_text = ' '.join(clean_text.split())
        
        return clean_text
    
    def _cache_verse_simple(self, verse_id, book_api_id, chapter, verse_number, text, reference):
        """Cache a verse from simple Bible API"""
        try:
            book = Book.objects.get(api_id=book_api_id)
            CachedVerse.objects.update_or_create(
                verse_id=verse_id,
                defaults={
                    'book': book,
                    'chapter': chapter,
                    'verse_number': verse_number,
                    'text': text,
                    'reference': reference
                }
            )
        except Book.DoesNotExist:
            print(f"Book not found: {book_api_id}")
        except Exception as e:
            print(f"Error caching verse: {e}")
    
    def _cache_verse_from_search(self, verse_data, clean_text):
        """Cache a verse from API.Bible search results"""
        try:
            verse_id = verse_data.get('id')
            reference = verse_data.get('reference', '')
            book_id = verse_data.get('bookId')
            
            if verse_id and clean_text:
                parts = verse_id.split('.')
                if len(parts) >= 3:
                    chapter = int(parts[1])
                    verse_num = int(parts[2])
                    
                    try:
                        book = Book.objects.get(api_id=book_id)
                        CachedVerse.objects.update_or_create(
                            verse_id=verse_id,
                            defaults={
                                'book': book,
                                'chapter': chapter,
                                'verse_number': verse_num,
                                'text': clean_text,
                                'reference': reference
                            }
                        )
                    except Book.DoesNotExist:
                        print(f"Book not found: {book_id}")
        except Exception as e:
            print(f"Error caching search verse: {e}")