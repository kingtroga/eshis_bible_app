from django.db import models
from django.utils import timezone
import json

class Book(models.Model):
    api_id = models.CharField(max_length=10, unique=True)  # e.g., "MAT"
    name = models.CharField(max_length=50)  # e.g., "Matthew"
    canonical_order = models.IntegerField()
    
    class Meta:
        ordering = ['canonical_order']
    
    def __str__(self):
        return self.name

class CachedVerse(models.Model):
    """Cache verses from API.Bible to reduce API calls"""
    verse_id = models.CharField(max_length=20, unique=True)  # e.g., "MAT.5.3"
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    chapter = models.IntegerField()
    verse_number = models.IntegerField()
    text = models.TextField()
    reference = models.CharField(max_length=50)  # e.g., "Matthew 5:3"
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['book__canonical_order', 'chapter', 'verse_number']
    
    def __str__(self):
        return f"{self.reference}"

class Quote(models.Model):
    """Predefined Jesus quotes from our QUOTES data"""
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    reference = models.CharField(max_length=100)  # e.g., "5:3-48"
    verse_ids = models.TextField()  # JSON list of verse IDs
    cached_verses = models.ManyToManyField(CachedVerse, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['book__canonical_order', 'reference']
        unique_together = ('book', 'reference')
    
    def get_verse_ids_list(self):
        """Return list of verse IDs from JSON field"""
        try:
            return json.loads(self.verse_ids or '[]')
        except:
            return []
    
    def set_verse_ids_list(self, verse_ids):
        """Set verse IDs as JSON"""
        self.verse_ids = json.dumps(verse_ids)
    
    def __str__(self):
        return f"{self.book.name} {self.reference}"

class SearchCache(models.Model):
    """Cache search results from API.Bible"""
    query = models.CharField(max_length=200, unique=True)
    results = models.TextField()  # JSON results
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def is_fresh(self, hours=24):
        """Check if cache is fresh (default 24 hours)"""
        return timezone.now() - self.created_at < timezone.timedelta(hours=hours)
    
    def get_results(self):
        """Get results as Python object"""
        try:
            return json.loads(self.results)
        except:
            return []