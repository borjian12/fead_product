from rest_framework import permissions


class IsAdmin(permissions.BasePermission):
    """Permission برای تأیید اینکه کاربر Admin است"""

    def has_permission(self, request, view):
        return hasattr(request.user, 'admin_profile')


class IsAgent(permissions.BasePermission):
    """Permission برای تأیید اینکه کاربر Agent است"""

    def has_permission(self, request, view):
        return hasattr(request.user, 'agent_profile')


class IsSeller(permissions.BasePermission):
    """Permission برای تأیید اینکه کاربر Seller است"""

    def has_permission(self, request, view):
        return hasattr(request.user, 'seller_profile')


class IsAdminOrSeller(permissions.BasePermission):
    """Permission برای تأیید اینکه کاربر Admin یا Seller است"""

    def has_permission(self, request, view):
        return hasattr(request.user, 'admin_profile') or hasattr(request.user, 'seller_profile')


class IsAdminOrAgent(permissions.BasePermission):
    """Permission برای تأیید اینکه کاربر Admin یا Agent است"""

    def has_permission(self, request, view):
        return hasattr(request.user, 'admin_profile') or hasattr(request.user, 'agent_profile')


class IsAdminOrSellerOrAgentForAssigned(permissions.BasePermission):
    """Permission برای Admin یا Seller یا Agent برای فروشندگان اختصاص‌یافته"""

    def has_permission(self, request, view):
        return (hasattr(request.user, 'admin_profile') or
                hasattr(request.user, 'seller_profile') or
                hasattr(request.user, 'agent_profile'))

    def has_object_permission(self, request, view, obj):
        user = request.user

        if hasattr(user, 'admin_profile'):
            return True

        if hasattr(user, 'seller_profile'):
            # بررسی تأیید شدن Seller
            if not user.seller_profile.is_approved:
                return False
            return obj.owner == user.seller_profile

        if hasattr(user, 'agent_profile'):
            # بررسی تأیید شدن Agent
            if not user.agent_profile.is_approved:
                return False
            # Agent می‌تواند محصولات فروشندگان اختصاص‌یافته به خود را ببیند
            return obj.owner in user.agent_profile.managed_sellers.all()

        return False


class IsAdminOrSelfSeller(permissions.BasePermission):
    """Permission برای Admin یا Seller برای محصولات خودش"""

    def has_permission(self, request, view):
        return hasattr(request.user, 'admin_profile') or hasattr(request.user, 'seller_profile')

    def has_object_permission(self, request, view, obj):
        user = request.user

        if hasattr(user, 'admin_profile'):
            return True

        if hasattr(user, 'seller_profile'):
            # بررسی تأیید شدن Seller
            if not user.seller_profile.is_approved:
                return False
            return obj.owner == user.seller_profile

        return False


class IsAdminOrAgentForAssigned(permissions.BasePermission):
    """Permission برای Admin یا Agent برای فروشندگان اختصاص‌یافته"""

    def has_permission(self, request, view):
        return hasattr(request.user, 'admin_profile') or hasattr(request.user, 'agent_profile')

    def has_object_permission(self, request, view, obj):
        user = request.user

        if hasattr(user, 'admin_profile'):
            return True

        if hasattr(user, 'agent_profile'):
            # بررسی تأیید شدن Agent
            if not user.agent_profile.is_approved:
                return False
            # Agent می‌تواند محصولات فروشندگان اختصاص‌یافته به خود را ببیند
            return obj.owner in user.agent_profile.managed_sellers.all()

        return False


class CanManageProductChannels(permissions.BasePermission):
    """Permission برای مدیریت کانال‌های محصول"""

    def has_permission(self, request, view):
        user = request.user

        if hasattr(user, 'admin_profile'):
            return user.admin_profile.can_manage_products

        if hasattr(user, 'seller_profile'):
            return user.seller_profile.is_approved

        if hasattr(user, 'agent_profile'):
            return user.agent_profile.is_approved

        return False