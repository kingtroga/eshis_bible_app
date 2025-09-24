from django.core.management.base import BaseCommand
from quotes.models import Quote
from quotes.tasks import verse_cache

class Command(BaseCommand):
    help = 'Cache all Jesus quotes verses immediately'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='Limit number of quotes to cache'
        )
    
    def handle(self, *args, **options):
        limit = options.get('limit')
        quotes = Quote.objects.all()
        
        if limit:
            quotes = quotes[:limit]
        
        total_quotes = quotes.count()
        self.stdout.write(f"Caching {total_quotes} quotes...")
        
        cached_count = 0
        for i, quote in enumerate(quotes, 1):
            try:
                verses_cached = verse_cache.cache_quote_immediately(quote)
                if verses_cached > 0:
                    cached_count += 1
                    self.stdout.write(f"[{i}/{total_quotes}] Cached {quote.book.name} {quote.reference} ({verses_cached} verses)")
                else:
                    self.stdout.write(f"[{i}/{total_quotes}] Already cached: {quote.book.name} {quote.reference}")
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"[{i}/{total_quotes}] Error caching {quote.book.name} {quote.reference}: {e}")
                )
        
        self.stdout.write(
            self.style.SUCCESS(f"Successfully processed {total_quotes} quotes, cached {cached_count} new ones")
        )
