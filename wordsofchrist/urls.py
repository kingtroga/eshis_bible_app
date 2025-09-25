from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/08087422585/', admin.site.urls),
    path('', include('quotes.urls')),
]

# Serve static files in development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler403 = "quotes.views.custom_permission_denied"
handler404 = "quotes.views.custom_page_not_found"
handler500 = "quotes.views.custom_server_error"