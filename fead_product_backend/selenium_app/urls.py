# selenium_app/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('submit/', views.submit_crawl_request, name='submit_crawl'),
    path('status/<str:request_id>/', views.get_request_status, name='get_crawl_status'),
]