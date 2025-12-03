# contract_manager/api_permissions.py
from rest_framework import permissions


class IsAdmin(permissions.BasePermission):
    """Permission برای تأیید اینکه کاربر Admin است"""

    def has_permission(self, request, view):
        return hasattr(request.user, 'admin_profile')


class IsAgent(permissions.BasePermission):
    """Permission برای تأیید اینکه کاربر Agent است"""

    def has_permission(self, request, view):
        return hasattr(request.user, 'agent')


class IsSeller(permissions.BasePermission):
    """Permission برای تأیید اینکه کاربر Seller است"""

    def has_permission(self, request, view):
        return hasattr(request.user, 'seller')


class IsAdminOrSeller(permissions.BasePermission):
    """Permission برای تأیید اینکه کاربر Admin یا Seller است"""

    def has_permission(self, request, view):
        return hasattr(request.user, 'admin_profile') or hasattr(request.user, 'seller')


class IsAdminOrAgent(permissions.BasePermission):
    """Permission برای تأیید اینکه کاربر Admin یا Agent است"""

    def has_permission(self, request, view):
        return hasattr(request.user, 'admin_profile') or hasattr(request.user, 'agent')


class IsAdminOrSelfSeller(permissions.BasePermission):
    """Permission برای Admin یا Seller فقط برای محصولات خودش"""

    def has_object_permission(self, request, view, obj):
        if hasattr(request.user, 'admin_profile'):
            return True
        if hasattr(request.user, 'seller'):
            return obj.owner == request.user.seller
        return False


class IsAdminOrAgentForAssigned(permissions.BasePermission):
    """Permission برای Admin یا Agent فقط برای فروشندگان اختصاص‌یافته"""

    def has_permission(self, request, view):
        if hasattr(request.user, 'admin_profile'):
            return True
        if hasattr(request.user, 'agent'):
            return True
        return False

    def has_object_permission(self, request, view, obj):
        if hasattr(request.user, 'admin_profile'):
            return True
        if hasattr(request.user, 'agent'):
            # Agent فقط می‌تواند فروشندگان اختصاص‌یافته به خود را ببیند
            return obj in request.user.agent.assigned_sellers.all()
        return False


class IsAdminOrSellerOrAgentForAssigned(permissions.BasePermission):
    """Permission برای Admin یا Seller یا Agent برای فروشندگان اختصاص‌یافته"""

    def has_permission(self, request, view):
        return hasattr(request.user, 'admin_profile') or hasattr(request.user, 'seller') or hasattr(request.user,
                                                                                                    'agent')

    def has_object_permission(self, request, view, obj):
        user = request.user

        if hasattr(user, 'admin_profile'):
            return True

        if hasattr(user, 'seller'):
            return obj.owner == user.seller

        if hasattr(user, 'agent'):
            return obj.owner in user.agent.assigned_sellers.all()

        return False


class CanManageProductChannels(permissions.BasePermission):
    """Permission برای مدیریت کانال‌های محصول"""

    def has_permission(self, request, view):
        return hasattr(request.user, 'admin_profile') or hasattr(request.user, 'seller') or hasattr(request.user,
                                                                                                    'agent')

    def has_object_permission(self, request, view, obj):
        user = request.user

        if hasattr(user, 'admin_profile'):
            return True

        if hasattr(user, 'seller'):
            return obj.owner == user.seller

        if hasattr(user, 'agent'):
            return obj.owner in user.agent.assigned_sellers.all()

        return False