import json
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics, permissions
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView

from django.contrib.auth import authenticate
from django.contrib.auth.hashers import check_password

from .models import (
    CustomUser, TelegramProfile, SellerProfile,
    AgentProfile, AdminProfile, BuyerProfile
)
from .serializers import (
    TelegramAuthSerializer, SellerRegisterSerializer, AgentRegisterSerializer,
    AdminCreateSerializer, LoginSerializer, VerificationSerializer,
    UserSerializer, SellerProfileSerializer, AgentProfileSerializer,
    AdminProfileSerializer, BuyerProfileSerializer, TelegramProfileSerializer,
    ApproveProfileSerializer, CreateBuyerByAdminSerializer
)
from .utils import verify_init_data
from .decorators import (
    jwt_or_telegram_auth_required, super_admin_required, admin_required,
    seller_required, agent_required, buyer_required
)


# ========== احراز هویت عمومی ==========

class SellerRegisterView(APIView):
    """ثبت نام فروشنده"""
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = SellerRegisterSerializer(data=request.data)
        if serializer.is_valid():
            seller = serializer.save()

            return Response({
                "detail": "ثبت نام موفقیت‌آمیز بود. کد تأیید به ایمیل شما ارسال شد.",
                "email": seller.user.email,
                "user_id": seller.user.id
            }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AgentRegisterView(APIView):
    """ثبت نام نماینده"""
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = AgentRegisterSerializer(data=request.data)
        if serializer.is_valid():
            agent = serializer.save()

            return Response({
                "detail": "ثبت نام موفقیت‌آمیز بود. کد تأیید به ایمیل شما ارسال شد.",
                "email": agent.user.email,
                "user_id": agent.user.id
            }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AdminCreateView(APIView):
    """ایجاد ادمین توسط سوپر ادمین"""
    permission_classes = [IsAuthenticated]

    @super_admin_required
    def post(self, request):
        serializer = AdminCreateSerializer(
            data=request.data,
            context={'request': request}
        )

        if serializer.is_valid():
            admin = serializer.save()

            return Response({
                "detail": "ادمین جدید با موفقیت ایجاد شد",
                "admin": AdminProfileSerializer(admin).data
            }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class TelegramAuthView(APIView):
    """احراز هویت تلگرام - فقط برای خریداران"""
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = TelegramAuthSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        init_data = serializer.validated_data["init_data"]
        parsed = verify_init_data(init_data)

        if not parsed:
            return Response(
                {"detail": "Invalid initData"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user_data = json.loads(parsed.get("user", "{}"))
        except json.JSONDecodeError:
            return Response(
                {"detail": "Invalid user data"},
                status=status.HTTP_400_BAD_REQUEST
            )

        telegram_id = user_data.get("id")
        if not telegram_id:
            return Response(
                {"detail": "Telegram ID not found"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # استخراج اطلاعات کاربر
        first_name = user_data.get("first_name", "")
        last_name = user_data.get("last_name", "")
        telegram_username = user_data.get("username", f"tg_{telegram_id}")
        language_code = user_data.get("language_code", "")
        is_premium = user_data.get("is_premium", False)
        photo_url = user_data.get("photo_url", "")

        # بررسی وجود کاربر تلگرام
        try:
            telegram_profile = TelegramProfile.objects.get(telegram_id=telegram_id)
            user = telegram_profile.user

            # به‌روزرسانی اطلاعات
            user.first_name = first_name
            user.last_name = last_name
            user.save()

            telegram_profile.first_name = first_name
            telegram_profile.last_name = last_name
            telegram_profile.username = telegram_username
            telegram_profile.language_code = language_code
            telegram_profile.is_premium = is_premium
            telegram_profile.photo_url = photo_url
            telegram_profile.save()

        except TelegramProfile.DoesNotExist:
            # ایجاد کاربر جدید برای خریدار
            username = f"buyer_{telegram_id}"
            email = f"tg_{telegram_id}@telegram.user"

            # ایجاد کاربر
            user = CustomUser.objects.create(
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name,
                is_verified=True  # خریداران تلگرام نیازی به تأیید ایمیل ندارند
            )

            # ایجاد پروفایل تلگرام
            telegram_profile = TelegramProfile.objects.create(
                user=user,
                telegram_id=telegram_id,
                username=telegram_username,
                first_name=first_name,
                last_name=last_name,
                language_code=language_code,
                is_premium=is_premium,
                photo_url=photo_url
            )

            # ایجاد پروفایل خریدار
            BuyerProfile.objects.create(user=user)

        # ایجاد توکن JWT
        refresh = RefreshToken.for_user(user)

        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": UserSerializer(user).data
        }, status=status.HTTP_200_OK)


class LoginView(APIView):
    """ورود به سیستم"""
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']

            # ایجاد توکن JWT
            refresh = RefreshToken.for_user(user)

            return Response({
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": UserSerializer(user).data
            }, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class VerifyEmailView(APIView):
    """تأیید ایمیل"""
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = VerificationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']

            # ایجاد توکن JWT
            refresh = RefreshToken.for_user(user)

            return Response({
                "detail": "حساب کاربری با موفقیت تأیید شد",
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": UserSerializer(user).data
            }, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ResendVerificationView(APIView):
    """ارسال مجدد کد تأیید"""
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email')

        if not email:
            return Response(
                {"email": "ایمیل را وارد کنید"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = CustomUser.objects.get(email=email)
        except CustomUser.DoesNotExist:
            return Response(
                {"email": "کاربری با این ایمیل یافت نشد"},
                status=status.HTTP_404_NOT_FOUND
            )

        if user.is_verified:
            return Response(
                {"detail": "حساب کاربری قبلاً تأیید شده است"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # ارسال مجدد کد
        user.generate_verification_code()

        return Response({
            "detail": "کد تأیید جدید به ایمیل شما ارسال شد"
        }, status=status.HTTP_200_OK)


# ========== مدیریت پروفایل‌ها ==========

class UserProfileView(APIView):
    """دریافت پروفایل کاربر"""

    @jwt_or_telegram_auth_required
    def get(self, request):
        user = request.user
        response_data = {
            "user": UserSerializer(user).data,
            "profiles": {}
        }

        # اضافه کردن پروفایل‌های موجود
        if user.has_admin_profile:
            response_data["profiles"]["admin"] = AdminProfileSerializer(user.admin_profile).data

        if user.has_seller_profile:
            response_data["profiles"]["seller"] = SellerProfileSerializer(user.seller_profile).data

        if user.has_agent_profile:
            response_data["profiles"]["agent"] = AgentProfileSerializer(user.agent_profile).data

        if user.has_buyer_profile:
            response_data["profiles"]["buyer"] = BuyerProfileSerializer(user.buyer_profile).data

        if user.has_telegram_profile:
            response_data["profiles"]["telegram"] = TelegramProfileSerializer(user.telegram_profile).data

        return Response(response_data)


class UpdateProfileView(APIView):
    """به‌روزرسانی پروفایل کاربر"""

    @jwt_or_telegram_auth_required
    def patch(self, request):
        user = request.user
        data = request.data

        # به‌روزرسانی اطلاعات کاربر
        if 'first_name' in data:
            user.first_name = data['first_name']
        if 'last_name' in data:
            user.last_name = data['last_name']

        user.save()

        # به‌روزرسانی پروفایل‌های مربوطه
        if user.has_seller_profile and 'company_name' in data:
            user.seller_profile.company_name = data['company_name']
            user.seller_profile.save()

        if user.has_agent_profile and 'company_name' in data:
            user.agent_profile.company_name = data['company_name']
            user.agent_profile.save()

        return Response({
            "detail": "پروفایل با موفقیت به‌روزرسانی شد",
            "user": UserSerializer(user).data
        })


# ========== مدیریت کاربران توسط ادمین ==========

class AdminUsersView(APIView):
    """مدیریت کاربران توسط ادمین"""

    @admin_required
    def get(self, request):
        """دریافت لیست کاربران"""
        users = CustomUser.objects.all().select_related(
            'admin_profile', 'seller_profile', 'agent_profile', 'buyer_profile'
        )

        user_data = []
        for user in users:
            user_info = UserSerializer(user).data

            # اضافه کردن اطلاعات پروفایل‌ها
            profiles = {}
            if user.has_admin_profile:
                profiles['admin'] = AdminProfileSerializer(user.admin_profile).data

            if user.has_seller_profile:
                profiles['seller'] = SellerProfileSerializer(user.seller_profile).data

            if user.has_agent_profile:
                profiles['agent'] = AgentProfileSerializer(user.agent_profile).data

            if user.has_buyer_profile:
                profiles['buyer'] = BuyerProfileSerializer(user.buyer_profile).data

            if user.has_telegram_profile:
                profiles['telegram'] = TelegramProfileSerializer(user.telegram_profile).data

            user_info['profiles'] = profiles
            user_data.append(user_info)

        return Response({
            "users": user_data,
            "count": len(user_data)
        })


class ApproveSellerView(APIView):
    """تأیید یا رد فروشنده توسط ادمین"""

    @admin_required
    def post(self, request, seller_id):
        try:
            seller = SellerProfile.objects.get(id=seller_id)
        except SellerProfile.DoesNotExist:
            return Response(
                {"detail": "فروشنده یافت نشد"},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = ApproveProfileSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        is_approved = serializer.validated_data['is_approved']

        if is_approved:
            seller.approve(request.user)
            message = "فروشنده با موفقیت تأیید شد"
        else:
            seller.disapprove()
            message = "فروشنده رد شد"

        return Response({
            "detail": message,
            "seller": SellerProfileSerializer(seller).data
        })


class ApproveAgentView(APIView):
    """تأیید یا رد نماینده توسط ادمین"""

    @admin_required
    def post(self, request, agent_id):
        try:
            agent = AgentProfile.objects.get(id=agent_id)
        except AgentProfile.DoesNotExist:
            return Response(
                {"detail": "نماینده یافت نشد"},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = ApproveProfileSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        is_approved = serializer.validated_data['is_approved']

        if is_approved:
            agent.approve(request.user)
            message = "نماینده با موفقیت تأیید شد"
        else:
            agent.disapprove()
            message = "نماینده رد شد"

        return Response({
            "detail": message,
            "agent": AgentProfileSerializer(agent).data
        })


class AssignSellerToAgentView(APIView):
    """اختصاص فروشنده به نماینده توسط ادمین"""

    @admin_required
    def post(self, request):
        seller_id = request.data.get('seller_id')
        agent_id = request.data.get('agent_id')

        if not seller_id or not agent_id:
            return Response(
                {"detail": "seller_id و agent_id الزامی هستند"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            seller = SellerProfile.objects.get(id=seller_id)
            agent = AgentProfile.objects.get(id=agent_id)
        except (SellerProfile.DoesNotExist, AgentProfile.DoesNotExist):
            return Response(
                {"detail": "فروشنده یا نماینده یافت نشد"},
                status=status.HTTP_404_NOT_FOUND
            )

        seller.assigned_agent = agent
        seller.save()

        return Response({
            "detail": f"فروشنده {seller.company_name} به نماینده {agent.company_name} اختصاص داده شد",
            "seller": SellerProfileSerializer(seller).data
        })


class CreateBuyerByAdminView(APIView):
    """ایجاد خریدار توسط ادمین/نماینده"""

    @jwt_or_telegram_auth_required
    def post(self, request):
        user = request.user

        # بررسی دسترسی
        if not (user.is_admin or user.is_super_admin or user.is_approved_agent):
            return Response(
                {"detail": "دسترسی غیرمجاز"},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = CreateBuyerByAdminSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data

        # بررسی وجود تلگرام آیدی
        if TelegramProfile.objects.filter(telegram_id=data['telegram_id']).exists():
            return Response(
                {"detail": "این آیدی تلگرام قبلاً ثبت شده است"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # ایجاد کاربر خریدار
        username = f"buyer_admin_{data['telegram_id']}"
        email = f"buyer_{data['telegram_id']}@system.user"

        user_obj = CustomUser.objects.create(
            username=username,
            email=email,
            first_name=data.get('first_name', ''),
            last_name=data.get('last_name', ''),
            is_verified=True
        )

        # ایجاد پروفایل تلگرام
        telegram_profile = TelegramProfile.objects.create(
            user=user_obj,
            telegram_id=data['telegram_id'],
            username=data['username'],
            first_name=data.get('first_name', ''),
            last_name=data.get('last_name', '')
        )

        # ایجاد پروفایل خریدار
        buyer_profile = BuyerProfile.objects.create(user=user_obj)

        # اختصاص به نماینده اگر مشخص شده باشد
        if 'assign_to_agent' in data and user.is_approved_agent:
            buyer_profile.assigned_agent = user.agent_profile
            buyer_profile.save()

        return Response({
            "detail": "خریدار با موفقیت ایجاد شد",
            "buyer": BuyerProfileSerializer(buyer_profile).data
        }, status=status.HTTP_201_CREATED)


class ApproveBuyerView(APIView):
    """تأیید یا رد خریدار توسط ادمین/نماینده"""

    @jwt_or_telegram_auth_required
    def post(self, request, buyer_id):
        user = request.user

        try:
            buyer = BuyerProfile.objects.get(id=buyer_id)
        except BuyerProfile.DoesNotExist:
            return Response(
                {"detail": "خریدار یافت نشد"},
                status=status.HTTP_404_NOT_FOUND
            )

        # بررسی دسترسی
        can_approve = False

        if user.is_admin or user.is_super_admin:
            can_approve = True
        elif user.is_approved_agent:
            # نماینده فقط می‌تواند خریداران خودش را تأیید کند
            if buyer.assigned_agent == user.agent_profile:
                can_approve = True

        if not can_approve:
            return Response(
                {"detail": "شما اجازه تأیید این خریدار را ندارید"},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = ApproveProfileSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        is_approved = serializer.validated_data['is_approved']

        if is_approved:
            buyer.approve(user)
            message = "خریدار با موفقیت تأیید شد"
        else:
            buyer.disapprove()
            message = "خریدار رد شد"

        return Response({
            "detail": message,
            "buyer": BuyerProfileSerializer(buyer).data
        })


# ========== مدیریت نمایندگان ==========

class AgentSellersView(APIView):
    """دریافت فروشندگان اختصاص‌یافته به نماینده"""

    @agent_required
    def get(self, request):
        user = request.user
        agent = user.agent_profile

        if agent.agent_type == 'internal':
            # نماینده داخلی همه فروشندگان را می‌بیند
            sellers = SellerProfile.objects.all()
        else:
            # نماینده خارجی فقط فروشندگان اختصاص‌یافته به خودش را می‌بیند
            sellers = agent.assigned_sellers.all()

        serializer = SellerProfileSerializer(sellers, many=True)

        return Response({
            "sellers": serializer.data,
            "count": sellers.count()
        })


class AgentBuyersView(APIView):
    """دریافت خریداران نماینده"""

    @agent_required
    def get(self, request):
        user = request.user
        agent = user.agent_profile

        if agent.agent_type == 'internal':
            # نماینده داخلی همه خریداران را می‌بیند
            buyers = BuyerProfile.objects.all()
        else:
            # نماینده خارجی فقط خریداران خودش را می‌بیند
            buyers = agent.assigned_buyers.all()

        serializer = BuyerProfileSerializer(buyers, many=True)

        return Response({
            "buyers": serializer.data,
            "count": buyers.count()
        })


# ========== آمار و گزارش‌ها ==========

class StatsView(APIView):
    """آمار کلی سیستم"""

    @admin_required
    def get(self, request):
        stats = {
            "total_users": CustomUser.objects.count(),
            "total_sellers": SellerProfile.objects.count(),
            "approved_sellers": SellerProfile.objects.filter(is_approved=True).count(),
            "total_agents": AgentProfile.objects.count(),
            "approved_agents": AgentProfile.objects.filter(is_approved=True).count(),
            "internal_agents": AgentProfile.objects.filter(agent_type='internal', is_approved=True).count(),
            "external_agents": AgentProfile.objects.filter(agent_type='external', is_approved=True).count(),
            "total_buyers": BuyerProfile.objects.count(),
            "approved_buyers": BuyerProfile.objects.filter(is_approved=True).count(),
            "telegram_users": TelegramProfile.objects.count(),
            "admins": AdminProfile.objects.count(),
            "super_admins": AdminProfile.objects.filter(role='super_admin').count(),
            "new_users_today": CustomUser.objects.filter(
                created_at__date=timezone.now().date()
            ).count(),
            "pending_approvals": {
                "sellers": SellerProfile.objects.filter(is_approved=False).count(),
                "agents": AgentProfile.objects.filter(is_approved=False).count(),
                "buyers": BuyerProfile.objects.filter(is_approved=False).count()
            }
        }

        return Response(stats)


# ========== توکن ==========

class CustomTokenRefreshView(TokenRefreshView):
    """رفرش توکن JWT"""
    pass