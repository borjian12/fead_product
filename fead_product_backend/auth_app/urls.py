# auth_app/urls.py
from django.urls import path
from .views import TelegramMiniAppAuthView, UserProfileView

urlpatterns = [
    path("telegram/miniapp/", TelegramMiniAppAuthView.as_view()),
    path("profile/", UserProfileView.as_view(), name="user-profile"),
]
