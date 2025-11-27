# auth_app/utils.py
import hmac
import hashlib
import urllib.parse
import time
import json
import jwt
from datetime import datetime, timedelta
from django.conf import settings


def verify_init_data(init_data: str) -> dict | None:
    """
    بررسی اعتبار initData دریافتی از تلگرام
    """
    try:
        parsed = dict(urllib.parse.parse_qsl(init_data, keep_blank_values=True))
        hash_received = parsed.pop("hash", None)

        if not hash_received:
            return None

        # ساخت data_check_string مطابق داکیومنت تلگرام
        data_check_string = "\n".join(
            f"{k}={v}" for k, v in sorted(parsed.items()) if k != "hash"
        )

        # تولید secret_key از bot token
        secret_key = hmac.new(
            b"WebAppData",
            settings.TELEGRAM_BOT_TOKEN.encode(),
            hashlib.sha256
        ).digest()

        # محاسبه hash
        hash_calc = hmac.new(
            secret_key,
            data_check_string.encode(),
            hashlib.sha256
        ).hexdigest()

        # مقایسه hash دریافتی و محاسبه شده
        if not hmac.compare_digest(hash_calc, hash_received):
            return None

        # بررسی زمان انقضا (۱ روز)
        auth_date = int(parsed.get("auth_date", 0))
        if time.time() - auth_date > 86400:  # 24 hours
            return None

        return parsed

    except Exception as e:
        print(f"Error verifying init data: {e}")
        return None


def generate_jwt(user_id: int) -> str:
    """
    تولید توکن JWT
    """
    now = datetime.utcnow()
    payload = {
        "user_id": user_id,
        "exp": now + timedelta(days=7),  # 7 روز اعتبار
        "iat": now,
        "type": "telegram_miniapp"
    }

    token = jwt.encode(
        payload,
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM
    )
    return token


def verify_jwt(token: str) -> dict | None:
    """
    بررسی اعتبار توکن JWT
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None