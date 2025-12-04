from functools import wraps
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import TokenError
import json

from .models import CustomUser, TelegramProfile
from .utils import verify_init_data


def jwt_or_telegram_auth_required(view_func):
    """
    دکوراتور برای احراز هویت JWT یا تلگرام
    """

    @wraps(view_func)
    def wrapper(self, request, *args, **kwargs):
        # بررسی JWT Token
        auth_header = request.headers.get('Authorization', '')

        if auth_header.startswith('Bearer '):
            token_str = auth_header.split(' ')[1]

            try:
                access_token = AccessToken(token_str)
                user_id_from_token = access_token.payload.get('user_id')

                if user_id_from_token:
                    try:
                        user_from_token = CustomUser.objects.get(id=user_id_from_token)
                        request.user = user_from_token
                        return view_func(self, request, *args, **kwargs)
                    except CustomUser.DoesNotExist:
                        pass
            except (TokenError, Exception):
                pass

        # بررسی Telegram Init Data
        init_data = request.headers.get('Telegram-Init-Data')
        if init_data:
            parsed = verify_init_data(init_data)
            if parsed:
                try:
                    user_data = json.loads(parsed.get("user", "{}"))
                    telegram_id = user_data.get("id")

                    if telegram_id:
                        try:
                            profile = TelegramProfile.objects.get(telegram_id=telegram_id)
                            request.user = profile.user
                            return view_func(self, request, *args, **kwargs)
                        except TelegramProfile.DoesNotExist:
                            pass
                except Exception:
                    pass

        return Response(
            {"detail": "Authentication required"},
            status=status.HTTP_401_UNAUTHORIZED
        )

    return wrapper


def super_admin_required(view_func):
    """دکوراتور برای سوپر ادمین"""

    @wraps(view_func)
    def wrapper(self, request, *args, **kwargs):
        user = request.user

        if not user.is_authenticated:
            return Response(
                {"detail": "Authentication required"},
                status=status.HTTP_401_UNAUTHORIZED
            )

        if not user.is_super_admin:
            return Response(
                {"detail": "Super admin privileges required"},
                status=status.HTTP_403_FORBIDDEN
            )

        return view_func(self, request, *args, **kwargs)

    return wrapper


def admin_required(view_func):
    """دکوراتور برای ادمین"""

    @wraps(view_func)
    def wrapper(self, request, *args, **kwargs):
        user = request.user

        if not user.is_authenticated:
            return Response(
                {"detail": "Authentication required"},
                status=status.HTTP_401_UNAUTHORIZED
            )

        if not (user.is_admin or user.is_super_admin):
            return Response(
                {"detail": "Admin privileges required"},
                status=status.HTTP_403_FORBIDDEN
            )

        return view_func(self, request, *args, **kwargs)

    return wrapper


def seller_required(view_func):
    """دکوراتور برای فروشنده تأیید شده"""

    @wraps(view_func)
    def wrapper(self, request, *args, **kwargs):
        user = request.user

        if not user.is_authenticated:
            return Response(
                {"detail": "Authentication required"},
                status=status.HTTP_401_UNAUTHORIZED
            )

        if not user.is_approved_seller:
            return Response(
                {"detail": "Approved seller account required"},
                status=status.HTTP_403_FORBIDDEN
            )

        return view_func(self, request, *args, **kwargs)

    return wrapper


def agent_required(view_func):
    """دکوراتور برای نماینده تأیید شده"""

    @wraps(view_func)
    def wrapper(self, request, *args, **kwargs):
        user = request.user

        if not user.is_authenticated:
            return Response(
                {"detail": "Authentication required"},
                status=status.HTTP_401_UNAUTHORIZED
            )

        if not user.is_approved_agent:
            return Response(
                {"detail": "Approved agent account required"},
                status=status.HTTP_403_FORBIDDEN
            )

        return view_func(self, request, *args, **kwargs)

    return wrapper


def buyer_required(view_func):
    """دکوراتور برای خریدار"""

    @wraps(view_func)
    def wrapper(self, request, *args, **kwargs):
        user = request.user

        if not user.is_authenticated:
            return Response(
                {"detail": "Authentication required"},
                status=status.HTTP_401_UNAUTHORIZED
            )

        if not user.has_buyer_profile:
            return Response(
                {"detail": "Buyer account required"},
                status=status.HTTP_403_FORBIDDEN
            )

        return view_func(self, request, *args, **kwargs)

    return wrapper