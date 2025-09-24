from django.core.management.base import BaseCommand
from quotes.models import Book, Quote
from quotes.bible_api import BibleAPIClient
from quotes.quotes_data import QUOTES

class Command(BaseCommand):
    help = 'Setup Bible books and populate Jesus quotes'
    
    def handle(self, *args, **options):
        client = BibleAPIClient()
        
        # Fetch and create books from API.Bible
        self.stdout.write("Fetching books from API.Bible...")
        books_data = client.get_books()
        
        # Map our book names to API book IDs and simple API names
        book_mapping = {
            'matthew': {'api_id': 'MAT', 'simple_name': 'matthew'},
            'mark': {'api_id': 'MRK', 'simple_name': 'mark'}, 
            'luke': {'api_id': 'LUK', 'simple_name': 'luke'},
            'john': {'api_id': 'JHN', 'simple_name': 'john'},
            'acts': {'api_id': 'ACT', 'simple_name': 'acts'},
            '1_corinthians': {'api_id': '1CO', 'simple_name': '1-corinthians'},
            '2_corinthians': {'api_id': '2CO', 'simple_name': '2-corinthians'},
            'revelation': {'api_id': 'REV', 'simple_name': 'revelation'}
        }
        
        canonical_order = {
            'matthew': 1, 'mark': 2, 'luke': 3, 'john': 4,
            'acts': 5, '1_corinthians': 6, '2_corinthians': 7,
            'revelation': 8
        }
        
        # Create books
        for book_name, book_info in book_mapping.items():
            api_id = book_info['api_id']
            
            # Find full name from API.Bible
            full_name = book_name.replace('_', ' ').title()
            for book_data in books_data:
                if book_data.get('id') == api_id:
                    full_name = book_data.get('name', full_name)
                    break
            
            book, created = Book.objects.get_or_create(
                api_id=api_id,
                defaults={
                    'name': full_name,
                    'canonical_order': canonical_order.get(book_name, 99)
                }
            )
            if created:
                self.stdout.write(f"Created book: {full_name} ({api_id})")
        
        # Create quotes with verse IDs
        self.stdout.write("Creating quotes...")
        for book_name, quote_refs in QUOTES.items():
            try:
                api_id = book_mapping[book_name]['api_id']
                book = Book.objects.get(api_id=api_id)
                
                for quote_ref in quote_refs:
                    quote, created = Quote.objects.get_or_create(
                        book=book,
                        reference=quote_ref
                    )
                    
                    if created:
                        # Generate verse IDs for this quote
                        chapter, verse_numbers = get_chapter_verse_from_quote(quote_ref)
                        verse_ids = []
                        
                        for verse_num in verse_numbers:
                            verse_id = f"{api_id}.{chapter}.{verse_num}"
                            verse_ids.append(verse_id)
                        
                        quote.set_verse_ids_list(verse_ids)
                        quote.save()
                        
                        self.stdout.write(f"Created quote: {book.name} {quote_ref}")
            
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"Error processing {book_name}: {e}")
                )
        
        self.stdout.write(
            self.style.SUCCESS("Successfully setup Bible data!")
        )

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