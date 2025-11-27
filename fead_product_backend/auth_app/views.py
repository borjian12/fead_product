# auth_app/views.py
import json

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.contrib.auth.models import User
from rest_framework_simplejwt.tokens import RefreshToken

from .models import TelegramProfile
from .serializers import UserProfileUpdateSerializer, TelegramProfileUpdateSerializer, TelegramAuthSerializer
from .utils import verify_init_data


# auth_app/views.py
class UserProfileView(APIView):
    """
    GET /api/auth/profile/ - دریافت اطلاعات پروفایل
    PATCH /api/auth/profile/ - به‌روزرسانی اطلاعات پروفایل
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        دریافت اطلاعات پروفایل کاربر
        """
        print(f"user--: {request.user}")
        try:
            user = request.user
            profile = TelegramProfile.objects.get(user=user)

            response_data = {
                "user": {
                    "id": user.id,
                    "username": f"user_{profile.telegram_id}",
                    "django_username": user.username,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "telegram_id": profile.telegram_id,
                    "language_code": profile.language_code,
                    "is_premium": profile.is_premium,
                    "photo_url": profile.photo_url,
                    "email": profile.email or "",
                    "people": profile.people or "",
                    "amazon_profile_link": profile.amazon_profile_link or "",
                    "amazon_reviews_count": profile.amazon_reviews_count or 0,
                    "amazon_purchases_count": profile.amazon_purchases_count or 0
                }
            }

            return Response(response_data)

        except TelegramProfile.DoesNotExist:
            return Response(
                {"detail": "Profile not found"},
                status=status.HTTP_404_NOT_FOUND
            )

    def patch(self, request):
        """
        به‌روزرسانی اطلاعات پروفایل با PATCH
        """
        try:
            print(f"user--: {request.user}")
            user = request.user
            profile = TelegramProfile.objects.get(user=user)

            # سریالایزر برای کاربر
            user_serializer = UserProfileUpdateSerializer(
                user,
                data=request.data,
                partial=True
            )

            # سریالایزر برای پروفایل تلگرام
            profile_serializer = TelegramProfileUpdateSerializer(
                profile,
                data=request.data,
                partial=True
            )

            user_updated = False
            profile_updated = False

            # به‌روزرسانی کاربر
            if user_serializer.is_valid():
                user_serializer.save()
                user_updated = True

            # به‌روزرسانی پروفایل
            if profile_serializer.is_valid():
                profile_serializer.save()
                profile_updated = True

            # اگر هیچ کدام معتبر نبودند
            if not user_updated and not profile_updated:
                errors = {}
                if user_serializer.errors:
                    errors.update(user_serializer.errors)
                if profile_serializer.errors:
                    errors.update(profile_serializer.errors)

                return Response(
                    {"detail": "Invalid data", "errors": errors},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # گرفتن اطلاعات به‌روز شده
            user.refresh_from_db()
            profile.refresh_from_db()

            response_data = {
                "detail": "Profile updated successfully",
                "user": {
                    "id": user.id,
                    "username": f"user_{profile.telegram_id}",
                    "django_username": user.username,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "telegram_id": profile.telegram_id,
                    "language_code": profile.language_code,
                    "is_premium": profile.is_premium,
                    "photo_url": profile.photo_url,
                    "email": profile.email or "",
                    "people": profile.people or "",
                    "amazon_profile_link": profile.amazon_profile_link or "",
                    "amazon_reviews_count": profile.amazon_reviews_count or 0,
                    "amazon_purchases_count": profile.amazon_purchases_count or 0
                }
            }

            return Response(response_data)

        except TelegramProfile.DoesNotExist:
            return Response(
                {"detail": "Profile not found"},
                status=status.HTTP_404_NOT_FOUND
            )

class TelegramMiniAppAuthView(APIView):
    """
    POST /api/auth/telegram/miniapp/
    body: { "init_data": "..." }
    """
    # authentication_classes = []
    # permission_classes = []

    def post(self, request):
        serializer = TelegramAuthSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        init_data = serializer.validated_data["init_data"]

        # بررسی و استخراج داده‌ها از initData
        parsed = verify_init_data(init_data)
        if not parsed:
            return Response({"detail": "Invalid initData"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user_data = json.loads(parsed.get("user", "{}"))
        except json.JSONDecodeError:
            return Response({"detail": "Invalid user data"}, status=status.HTTP_400_BAD_REQUEST)

        if not user_data:
            return Response({"detail": "User data not found"}, status=status.HTTP_400_BAD_REQUEST)

        telegram_id = user_data.get("id")
        if not telegram_id:
            return Response({"detail": "Telegram ID not found"}, status=status.HTTP_400_BAD_REQUEST)

        # استخراج اطلاعات کاربر از تلگرام
        first_name = user_data.get("first_name", "")
        last_name = user_data.get("last_name", "")
        username = user_data.get("username", f"tg_{telegram_id}")
        language_code = user_data.get("language_code", "")
        is_premium = user_data.get("is_premium", False)
        photo_url = user_data.get("photo_url", "")

        # استفاده از telegram_id به عنوان username در Django User
        django_username = f"tg_{telegram_id}"
        display_username = username or f"user_{telegram_id}"

        # ایجاد یا به‌روزرسانی کاربر
        try:
            profile = TelegramProfile.objects.select_related('user').get(telegram_id=telegram_id)
            user = profile.user

            # به‌روزرسانی اطلاعات کاربر
            user.username = django_username
            user.first_name = first_name
            user.last_name = last_name
            user.save()

            # به‌روزرسانی پروفایل تلگرام
            profile.language_code = language_code
            profile.is_premium = is_premium
            profile.photo_url = photo_url
            profile.save()

        except TelegramProfile.DoesNotExist:
            # ایجاد کاربر جدید
            user = User.objects.create(
                username=django_username,
                first_name=first_name,
                last_name=last_name
            )
            profile = TelegramProfile.objects.create(
                user=user,
                telegram_id=telegram_id,
                language_code=language_code,
                is_premium=is_premium,
                photo_url=photo_url
            )

        # ایجاد توکن JWT
        refresh = RefreshToken.for_user(user)

        response_data = {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": {
                "id": user.id,
                "username": display_username,
                "django_username": django_username,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "telegram_id": telegram_id,
                "language_code": language_code,
                "is_premium": is_premium,
                "photo_url": photo_url,
                "email": profile.email or "",
                "people": profile.people or "",
                "amazon_profile_link": profile.amazon_profile_link or "",
                "amazon_reviews_count": profile.amazon_reviews_count or 0,
                "amazon_purchases_count": profile.amazon_purchases_count or 0
            }
        }

        return Response(response_data, status=status.HTTP_200_OK)