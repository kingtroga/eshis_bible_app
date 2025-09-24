from django.core.management.base import BaseCommand
from django.db import transaction
from quotes.models import Quote, CachedVerse
from quotes.bible_api import BibleAPIClient
import time

class Command(BaseCommand):
    help = 'Safely cache quotes one by one'
    
    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=10, help='Number of quotes to cache')
        parser.add_argument('--delay', type=float, default=2.0, help='Delay between quotes in seconds')
    
    def handle(self, *args, **options):
        limit = options['limit']
        delay = options['delay']
        
        client = BibleAPIClient()
        uncached_quotes = Quote.objects.filter(cached_verses__isnull=True).distinct()[:limit]
        
        self.stdout.write(f"Found {uncached_quotes.count()} uncached quotes")
        
        for i, quote in enumerate(uncached_quotes, 1):
            self.stdout.write(f"[{i}/{len(uncached_quotes)}] Caching {quote.book.name} {quote.reference}...")
            
            verse_ids = quote.get_verse_ids_list()
            cached_count = 0
            
            for verse_id in verse_ids:
                try:
                    # Check if exists
                    if CachedVerse.objects.filter(verse_id=verse_id).exists():
                        cached_verse = CachedVerse.objects.get(verse_id=verse_id)
                        quote.cached_verses.add(cached_verse)
                        continue
                    
                    # Fetch from API
                    verse_data = client.get_verse(verse_id)
                    if verse_data:
                        with transaction.atomic():
                            cached_verse, created = CachedVerse.objects.get_or_create(
                                verse_id=verse_id,
                                defaults={
                                    'book': quote.book,
                                    'chapter': int(verse_id.split('.')[1]),
                                    'verse_number': int(verse_id.split('.')[2]),
                                    'text': verse_data['text'],
                                    'reference': verse_data['reference']
                                }
                            )
                            quote.cached_verses.add(cached_verse)
                            
                        if created:
                            cached_count += 1
                        
                        time.sleep(0.5)  # Be nice to API
                        
                except Exception as e:
                    self.stdout.write(f"  Error with {verse_id}: {e}")
            
            self.stdout.write(f"  Cached {cached_count} new verses")
            
            # Delay between quotes
            if i < len(uncached_quotes):
                time.sleep(delay)
        
        self.stdout.write(self.style.SUCCESS("Done!"))