# selenium_app/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # API برای درایورها
    path('drivers/', views.SeleniumDriverListCreateView.as_view(), name='driver-list-create'),
    path('drivers/<str:name>/', views.SeleniumDriverDetailView.as_view(), name='driver-detail'),

    # API برای درخواست‌های کراول
    path('requests/', views.CrawlRequestListView.as_view(), name='crawl-request-list'),
    path('requests/submit/', views.submit_crawl_request, name='submit-crawl'),
    path('requests/<str:request_id>/', views.CrawlRequestDetailView.as_view(), name='crawl-request-detail'),
    path('requests/status/<str:request_id>/', views.get_request_status, name='get-crawl-status'),

    # API برای sessionها
    path('sessions/', views.DriverSessionListView.as_view(), name='session-list'),
    path('sessions/<str:session_id>/', views.DriverSessionDetailView.as_view(), name='session-detail'),

    # API برای آمار
    path('stats/', views.get_crawl_stats, name='crawl-stats'),
]