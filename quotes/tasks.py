import time
from django.utils import timezone
from django.db import transaction
from django.db.models import Q
from .models import Quote, CachedVerse
from .bible_api import BibleAPIClient

class VerseCache:
    _instance = None
    _lock = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def cache_quote_immediately(self, quote):
        """Cache a specific quote's verses immediately - SYNCHRONOUS"""
        if self._lock:
            return 0  # Skip if already processing
            
        self._lock = True
        try:
            return self._do_cache_quote(quote)
        finally:
            self._lock = False
    
    def _do_cache_quote(self, quote):
        """Actually cache the quote verses"""
        client = BibleAPIClient()
        verse_ids = quote.get_verse_ids_list()
        
        cached_count = 0
        for verse_id in verse_ids:
            try:
                # Check if already cached
                if CachedVerse.objects.filter(verse_id=verse_id).exists():
                    cached_verse = CachedVerse.objects.get(verse_id=verse_id)
                    quote.cached_verses.add(cached_verse)
                    continue
                
                # Fetch from API
                verse_data = client.get_verse(verse_id)
                if verse_data:
                    # Check again after API call (avoid race conditions)
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
                        print(f"Cached verse: {verse_id}")
                    
                    # Small delay to be nice to APIs
                    time.sleep(0.5)
                    
            except Exception as e:
                print(f"Error caching verse {verse_id}: {e}")
                continue
        
        return cached_count
    
    def cache_random_quotes(self, max_quotes=3):
        """Cache a few random uncached quotes - called on-demand"""
        if self._lock:
            return 0
            
        try:
            # Get quotes without cached verses
            uncached_quotes = Quote.objects.filter(
                cached_verses__isnull=True
            ).distinct()[:max_quotes]
            
            total_cached = 0
            for quote in uncached_quotes:
                cached = self.cache_quote_immediately(quote)
                total_cached += cached
            
            return total_cached
            
        except Exception as e:
            print(f"Error in cache_random_quotes: {e}")
            return 0

# Global instance
verse_cache = VerseCache()