# contract_manager/urls_api.py (API با JWT)
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import api_jwt
from .api_jwt import SellerManagementAPIView, AgentManagementAPIView

router = DefaultRouter()
router.register(r'products', api_jwt.ProductViewSet, basename='product')

app_name = 'contract_manager_api'

urlpatterns = [
    # Products CRUD
    path('', include(router.urls)),

    # Countries
    path('countries/', api_jwt.CountriesAPIView.as_view(), name='countries'),

    # Tools
    path('tools/verify-url/', api_jwt.VerifyURLAPIView.as_view(), name='verify_url'),

    # Bulk operations
    path('bulk/refresh/', api_jwt.BulkRefreshAPIView.as_view(), name='bulk_refresh'),
    path('bulk/send/', api_jwt.BulkSendAPIView.as_view(), name='bulk_send'),
    path('admin/sellers/', SellerManagementAPIView.as_view(), name='admin-sellers'),
    path('admin/sellers/<uuid:seller_id>/', SellerManagementAPIView.as_view(), name='admin-seller-detail'),
    path('admin/agents/', AgentManagementAPIView.as_view(), name='admin-agents'),
    path('admin/agents/<uuid:agent_id>/', AgentManagementAPIView.as_view(), name='admin-agent-detail'),
]