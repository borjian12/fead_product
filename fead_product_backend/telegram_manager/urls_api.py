from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from . import api_views as views

router = DefaultRouter()
router.register(r'channels', views.TelegramChannelViewSet, basename='channel')
router.register(r'messages', views.TelegramMessageViewSet, basename='message')
router.register(r'edit-history', views.MessageEditHistoryViewSet, basename='edit-history')
router.register(r'sending-logs', views.MessageSendingLogViewSet, basename='sending-log')

urlpatterns = [
    # Authentication URLs
    # Main API
    path('', include(router.urls)),

    # Utility APIs
    path('send-direct/', views.SendDirectMessageAPI.as_view(), name='send_direct'),
    path('bulk-send/', views.BulkSendAPI.as_view(), name='bulk_send'),
    path('bot-info/', views.BotInfoAPI.as_view(), name='bot_info'),
    path('dashboard-stats/', views.get_dashboard_stats, name='dashboard_stats'),

    # Channel specific
    path('channels/<uuid:pk>/messages/',
         views.TelegramChannelViewSet.as_view({'get': 'channel_messages'}),
         name='channel-messages'),
]