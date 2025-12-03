# contract_manager/urls.py (HTML views)
from django.urls import path
from . import views

app_name = 'contract_manager'

urlpatterns = [
    path('', views.product_list, name='product_list'),
    path('create/', views.create_product, name='create_product'),
    path('product/<uuid:product_id>/', views.product_detail, name='product_detail'),
    path('product/<uuid:product_id>/send/', views.send_to_telegram, name='send_to_telegram'),
    path('product/<uuid:product_id>/refresh/', views.refresh_product_data, name='refresh_product_data'),
    path('product/<uuid:product_id>/edit/', views.edit_product, name='edit_product'),
]