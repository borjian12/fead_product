# amazon_app/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('crawl/', views.crawl_products, name='crawl_products'),
    path('product/<str:asin>/', views.get_product_info, name='get_product_info'),
    path('product/<str:asin>/history/', views.get_price_history, name='get_price_history'),
    path('stats/', views.get_crawl_stats, name='get_crawl_stats'),
]