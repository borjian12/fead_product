# amazon_app/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('products/', views.ListProductsAPIView.as_view(), name='list_products'),
    path('products/<str:asin>/', views.GetProductDetailAPIView.as_view(), name='product_detail'),
    path('crawl/', views.CrawlProductsAPIView.as_view(), name='crawl_products'),
    path('crawl-single/', views.CrawlSingleProductAPIView.as_view(), name='crawl_single_product'),
    path('crawl-by-url/', views.CrawlByURLAPIView.as_view(), name='crawl_by_url'),
    path('verify-match/', views.VerifyProductMatchAPIView.as_view(), name='verify_product_match'),
    path('products/<str:asin>/history/', views.GetPriceHistoryAPIView.as_view(), name='price_history'),
    path('stats/', views.GetCrawlStatsAPIView.as_view(), name='crawl_stats'),
]