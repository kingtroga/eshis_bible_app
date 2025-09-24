from django.urls import path
from . import views

app_name = 'quotes'

urlpatterns = [
    path('', views.home, name='home'),
    path('quote/<int:quote_id>/', views.quote_detail, name='detail'),
    path('api/quotes/', views.api_quotes, name='api_quotes'),
    path('api/cache-verses/', views.cache_verses_view, name='cache_verses'),
]