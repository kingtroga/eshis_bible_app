from django.contrib import admin
from .models import Book, Quote, CachedVerse, SearchCache

@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ('name', 'api_id', 'canonical_order')
    ordering = ('canonical_order',)

@admin.register(Quote)
class QuoteAdmin(admin.ModelAdmin):
    list_display = ('book', 'reference', 'created_at')
    list_filter = ('book', 'created_at')
    ordering = ('book__canonical_order', 'reference')

@admin.register(CachedVerse)
class CachedVerseAdmin(admin.ModelAdmin):
    list_display = ('reference', 'book', 'chapter', 'verse_number', 'created_at')
    list_filter = ('book', 'created_at')
    search_fields = ('text', 'reference')
    ordering = ('book__canonical_order', 'chapter', 'verse_number')

@admin.register(SearchCache)
class SearchCacheAdmin(admin.ModelAdmin):
    list_display = ('query', 'created_at')
    ordering = ('-created_at',)