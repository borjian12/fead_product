# amazon_app/permissions.py
from rest_framework import permissions
import logging

logger = logging.getLogger(__name__)


class IsAdminForAmazonAPI(permissions.BasePermission):
    """
    Permission برای تأیید اینکه کاربر Admin است و می‌تواند از Amazon API استفاده کند
    """

    def has_permission(self, request, view):
        # بررسی احراز هویت
        if not request.user:
            logger.warning("No user object in request")
            return False

        if not request.user.is_authenticated:
            logger.warning(f"User not authenticated: {request.user}")
            return False

        # بررسی سوپر یوزر
        if request.user.is_superuser:
            logger.info(f"Access granted - Superuser: {request.user.username}")
            return True

        # بررسی admin_profile
        if hasattr(request.user, 'admin_profile'):
            logger.info(f"Access granted - Admin Profile: {request.user.username}")
            return True

        logger.warning(
            f"Access denied - User: {request.user.username}, is_superuser: {request.user.is_superuser}, has_admin_profile: {hasattr(request.user, 'admin_profile')}")
        return False