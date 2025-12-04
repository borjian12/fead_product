from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import api_jwt

router = DefaultRouter()
router.register(r'products', api_jwt.ProductViewSet, basename='product')

app_name = 'contract_manager_api'

urlpatterns = [
    # Products CRUD
    path('', include(router.urls)),

    # Products specific endpoints
    path('products/<uuid:pk>/refresh/', api_jwt.ProductViewSet.as_view({'post': 'refresh'}), name='product-refresh'),
    path('products/<uuid:pk>/send-to-channels/', api_jwt.ProductViewSet.as_view({'post': 'send_to_channels'}), name='product-send-to-channels'),
    path('products/<uuid:pk>/stop/', api_jwt.ProductViewSet.as_view({'post': 'stop'}), name='product-stop'),
    path('products/<uuid:pk>/resume/', api_jwt.ProductViewSet.as_view({'post': 'resume'}), name='product-resume'),
    path('products/<uuid:pk>/assign-to-seller/', api_jwt.ProductViewSet.as_view({'post': 'assign_to_seller'}), name='product-assign-to-seller'),
    path('products/bulk-actions/', api_jwt.ProductViewSet.as_view({'post': 'bulk_actions'}), name='product-bulk-actions'),

    # Countries
    path('countries/', api_jwt.CountriesAPIView.as_view(), name='countries'),

    # Channels
    path('channels/', api_jwt.ChannelAPIView.as_view(), name='channels'),
    path('products/<uuid:product_id>/channels/', api_jwt.ProductChannelsAPIView.as_view(), name='product-channels'),
    path('products/<uuid:product_id>/messages/', api_jwt.ProductMessagesAPIView.as_view(), name='product-messages'),

    # Tools
    path('tools/verify-url/', api_jwt.VerifyURLAPIView.as_view(), name='verify_url'),

    # Bulk operations
    path('bulk/refresh/', api_jwt.BulkRefreshAPIView.as_view(), name='bulk_refresh'),
    path('bulk/send/', api_jwt.BulkSendAPIView.as_view(), name='bulk_send'),

    # Admin management
    path('admin/dashboard/stats/', api_jwt.DashboardStatsAPIView.as_view(), name='admin-dashboard-stats'),
    path('admin/sellers/', api_jwt.SellerManagementAPIView.as_view(), name='admin-sellers'),
    path('admin/agents/', api_jwt.AgentManagementAPIView.as_view(), name='admin-agents'),
]