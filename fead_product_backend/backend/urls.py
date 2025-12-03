from django.contrib import admin
from django.urls import path, include, re_path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework import permissions
from django.conf import settings

# Schema view
schema_view = get_schema_view(
    openapi.Info(
        title="Telegram Manager API",
        default_version='v1',
        description="API for managing Telegram channels and messages",
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="contact@example.com"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
)

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),

    # API ها - با حفظ backward compatibility
    path('api/auth/', include('auth_app.urls')),
    path('api/crawl/', include('selenium_app.urls')),
    path('api/amazon/', include('amazon_app.urls')),

    # JWT Authentication
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/token/verify/', TokenVerifyView.as_view(), name='token_verify'),

    # Telegram Manager HTML views (ساختار فعلی)
    path('telegram-manager/', include('telegram_manager.urls')),
    path('api/telegram/', include('telegram_manager.urls_api')),

    # Contract Manager
    path('contracts/', include('contract_manager.urls')),  # HTML views
    path('api/contracts/', include('contract_manager.urls_api')),  # API با JWT

    # Swagger URLs - اصلاح شده
    re_path(r'^swagger(?P<format>\.json|\.yaml)$',
            schema_view.without_ui(cache_timeout=0),
            name='schema-json'),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0),
         name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0),
         name='schema-redoc'),

    # API Documentation با prefix متفاوت (اختیاری)
    path('api-docs/', schema_view.with_ui('swagger', cache_timeout=0),
         name='api-docs'),
]

# برای دیباگ
if settings.DEBUG:
    from django.conf.urls.static import static

    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)