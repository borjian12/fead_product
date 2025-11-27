# auth_app/decorators.py
from functools import wraps
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.models import User
from .models import TelegramProfile
from .utils import verify_init_data
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import TokenError
import json


def telegram_auth_required(view_func):
    @wraps(view_func)
    def wrapper(self, request, *args, **kwargs):
        print("🚨 ===== telegram_auth_required DECORATOR CALLED =====")
        print(f"📡 Method: {request.method}")
        print(f"🌐 Path: {request.path}")
        print(f"📋 Headers keys: {list(request.headers.keys())}")

        # 🔥 لاگ کردن توکن دریافتی
        auth_header = request.headers.get('Authorization', '')
        print(f"🔑 Authorization Header: {auth_header}")

        if auth_header.startswith('Bearer '):
            token_str = auth_header.split(' ')[1]
            print(f"🔑 Token received (first 50 chars): {token_str[:50]}...")

            try:
                # decode کردن توکن
                access_token = AccessToken(token_str)
                user_id_from_token = access_token.payload.get('user_id')
                token_type = access_token.payload.get('token_type')

                print(f"🔍 Decoded Token Info:")
                print(f"   - User ID in token: {user_id_from_token}")
                print(f"   - Token type: {token_type}")
                print(f"   - Expiry: {access_token.payload.get('exp')}")

                # پیدا کردن کاربر از روی توکن
                if user_id_from_token:
                    try:
                        user_from_token = User.objects.get(id=user_id_from_token)
                        print(f"✅ User from token: {user_from_token.username} (ID: {user_from_token.id})")

                        # ست کردن کاربر در request
                        request.user = user_from_token
                        request.user_id = user_from_token.id
                        print(f"🎯 User authenticated via JWT: {user_from_token.username}")
                        return view_func(self, request, *args, **kwargs)

                    except User.DoesNotExist:
                        print(f"❌ User not found for ID: {user_id_from_token}")

            except TokenError as e:
                print(f"❌ JWT Token error: {e}")
            except Exception as e:
                print(f"❌ Error decoding token: {e}")
        else:
            print("❌ No Bearer token found in Authorization header")

        # بررسی Telegram Init Data به عنوان fallback
        init_data = request.headers.get('Telegram-Init-Data')
        if init_data:
            print(f"📱 Telegram Init Data found: {init_data[:50]}...")
            parsed = verify_init_data(init_data)
            if parsed:
                try:
                    user_data = json.loads(parsed.get("user", "{}"))
                    telegram_id = user_data.get("id")

                    if telegram_id:
                        print(f"✅ Telegram user found: {telegram_id}")
                        try:
                            profile = TelegramProfile.objects.get(telegram_id=telegram_id)
                            request.user = profile.user
                            request.user_id = profile.user.id
                            print(f"✅ Telegram User authenticated: {profile.user.username} (ID: {profile.user.id})")
                            return view_func(self, request, *args, **kwargs)
                        except TelegramProfile.DoesNotExist:
                            print(f"❌ Telegram profile not found: {telegram_id}")
                except Exception as e:
                    print(f"❌ Error parsing Telegram data: {e}")

        print("❌ NO AUTHENTICATION METHOD SUCCEEDED")
        return Response(
            {"detail": "Authentication required"},
            status=status.HTTP_401_UNAUTHORIZED
        )

    return wrapper