from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.utils import timezone
from .models import (
    CustomUser, TelegramProfile, SellerProfile,
    AgentProfile, AdminProfile, BuyerProfile
)


class UserSerializer(serializers.ModelSerializer):
    """سریالایزر کاربر اصلی"""

    class Meta:
        model = CustomUser
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'is_verified', 'is_active', 'date_joined', 'created_at'
        ]
        read_only_fields = ['id', 'is_verified', 'date_joined', 'created_at']


class UserRegisterSerializer(serializers.ModelSerializer):
    """ثبت نام کاربر (برای Seller و Agent)"""

    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    password2 = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'}
    )

    class Meta:
        model = CustomUser
        fields = [
            'username', 'email', 'password', 'password2',
            'first_name', 'last_name'
        ]
        extra_kwargs = {
            'username': {'required': True},
            'email': {'required': True},
        }

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({
                "password": "رمز عبور و تأیید آن مطابقت ندارند"
            })

        # بررسی ایمیل تکراری
        if CustomUser.objects.filter(email=attrs['email']).exists():
            raise serializers.ValidationError({
                "email": "این ایمیل قبلاً ثبت شده است"
            })

        # بررسی نام کاربری تکراری
        if CustomUser.objects.filter(username=attrs['username']).exists():
            raise serializers.ValidationError({
                "username": "این نام کاربری قبلاً ثبت شده است"
            })

        return attrs

    def create(self, validated_data):
        validated_data.pop('password2')
        user = CustomUser.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', '')
        )
        user.generate_verification_code()
        return user


class SellerRegisterSerializer(serializers.ModelSerializer):
    """ثبت نام فروشنده"""

    user = UserRegisterSerializer()

    class Meta:
        model = SellerProfile
        fields = [
            'user', 'company_name', 'contact_email', 'contact_phone',
            'website', 'address', 'tax_id'
        ]
        extra_kwargs = {
            'company_name': {'required': True},
            'contact_email': {'required': True},
            'contact_phone': {'required': True},
        }

    def validate(self, attrs):
        # بررسی ایمیل تماس تکراری
        contact_email = attrs.get('contact_email')
        if SellerProfile.objects.filter(contact_email=contact_email).exists():
            raise serializers.ValidationError({
                "contact_email": "این ایمیل تماس قبلاً ثبت شده است"
            })

        return attrs

    def create(self, validated_data):
        user_data = validated_data.pop('user')
        user_serializer = UserRegisterSerializer(data=user_data)

        if user_serializer.is_valid():
            user = user_serializer.save()

            # ایجاد پروفایل فروشنده
            seller = SellerProfile.objects.create(
                user=user,
                contact_email=validated_data.get('contact_email', user.email),
                **{k: v for k, v in validated_data.items() if k != 'contact_email'}
            )
            return seller

        raise serializers.ValidationError(user_serializer.errors)


class AgentRegisterSerializer(serializers.ModelSerializer):
    """ثبت نام نماینده"""

    user = UserRegisterSerializer()

    class Meta:
        model = AgentProfile
        fields = [
            'user', 'agent_type', 'company_name', 'contact_email',
            'contact_phone', 'website', 'address', 'commission_rate'
        ]
        extra_kwargs = {
            'company_name': {'required': True},
            'contact_email': {'required': True},
            'contact_phone': {'required': True},
            'commission_rate': {'required': True, 'min_value': 0, 'max_value': 100},
        }

    def validate(self, attrs):
        # بررسی ایمیل تماس تکراری
        contact_email = attrs.get('contact_email')
        if AgentProfile.objects.filter(contact_email=contact_email).exists():
            raise serializers.ValidationError({
                "contact_email": "این ایمیل تماس قبلاً ثبت شده است"
            })

        return attrs

    def create(self, validated_data):
        user_data = validated_data.pop('user')
        user_serializer = UserRegisterSerializer(data=user_data)

        if user_serializer.is_valid():
            user = user_serializer.save()

            # ایجاد پروفایل نماینده
            agent = AgentProfile.objects.create(
                user=user,
                contact_email=validated_data.get('contact_email', user.email),
                **{k: v for k, v in validated_data.items() if k != 'contact_email'}
            )
            return agent

        raise serializers.ValidationError(user_serializer.errors)


class AdminCreateSerializer(serializers.ModelSerializer):
    """ایجاد ادمین توسط سوپر ادمین"""

    user = UserRegisterSerializer()

    class Meta:
        model = AdminProfile
        fields = [
            'user', 'role', 'can_manage_users', 'can_manage_products',
            'can_manage_contracts', 'can_manage_settings'
        ]
        extra_kwargs = {
            'role': {'required': True},
        }

    def create(self, validated_data):
        user_data = validated_data.pop('user')
        created_by = self.context['request'].user

        user_serializer = UserRegisterSerializer(data=user_data)

        if user_serializer.is_valid():
            user = user_serializer.save()
            user.is_verified = True  # ادمین نیازی به تأیید ایمیل ندارد
            user.save()

            # ایجاد پروفایل ادمین
            admin = AdminProfile.objects.create(
                user=user,
                created_by=created_by,
                **validated_data
            )
            return admin

        raise serializers.ValidationError(user_serializer.errors)


class TelegramAuthSerializer(serializers.Serializer):
    """سریالایزر احراز هویت تلگرام"""
    init_data = serializers.CharField(required=True, max_length=2000)

    def validate_init_data(self, value):
        if not value or len(value) < 50:
            raise serializers.ValidationError("init_data نامعتبر است")
        return value


class LoginSerializer(serializers.Serializer):
    """ورود به سیستم"""
    username = serializers.CharField(required=True)
    password = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'}
    )

    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')

        if username and password:
            user = authenticate(username=username, password=password)

            if not user:
                raise serializers.ValidationError("نام کاربری یا رمز عبور اشتباه است")

            if not user.is_active:
                raise serializers.ValidationError("حساب کاربری غیرفعال است")

            if not user.is_verified:
                raise serializers.ValidationError("لطفاً ابتدا ایمیل خود را تأیید کنید")

            # بررسی وضعیت پروفایل‌ها
            if user.has_seller_profile and not user.seller_profile.is_approved:
                raise serializers.ValidationError("حساب فروشنده هنوز توسط ادمین تأیید نشده است")

            if user.has_agent_profile and not user.agent_profile.is_approved:
                raise serializers.ValidationError("حساب نماینده هنوز توسط ادمین تأیید نشده است")

            attrs['user'] = user
            return attrs

        raise serializers.ValidationError("نام کاربری و رمز عبور را وارد کنید")


class VerificationSerializer(serializers.Serializer):
    """تأیید کد ایمیل"""
    email = serializers.EmailField(required=True)
    code = serializers.CharField(max_length=6, required=True)

    def validate(self, attrs):
        email = attrs.get('email')
        code = attrs.get('code')

        try:
            user = CustomUser.objects.get(email=email)
        except CustomUser.DoesNotExist:
            raise serializers.ValidationError({"email": "کاربری با این ایمیل یافت نشد"})

        if user.is_verified:
            raise serializers.ValidationError("حساب کاربری قبلاً تأیید شده است")

        if not user.verify_code(code):
            raise serializers.ValidationError({"code": "کد تأیید نامعتبر یا منقضی شده است"})

        attrs['user'] = user
        return attrs


class PasswordResetRequestSerializer(serializers.Serializer):
    """درخواست ریست پسورد"""
    email = serializers.EmailField(required=True)

    def validate(self, attrs):
        email = attrs.get('email')

        try:
            user = CustomUser.objects.get(email=email)
        except CustomUser.DoesNotExist:
            raise serializers.ValidationError({"email": "کاربری با این ایمیل یافت نشد"})

        if not user.is_active:
            raise serializers.ValidationError("حساب کاربری غیرفعال است")

        attrs['user'] = user
        return attrs


class PasswordResetConfirmSerializer(serializers.Serializer):
    """تأیید ریست پسورد"""
    token = serializers.CharField(required=True)
    new_password = serializers.CharField(
        required=True,
        validators=[validate_password],
        write_only=True,
        style={'input_type': 'password'}
    )
    new_password2 = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'}
    )

    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password2']:
            raise serializers.ValidationError({
                "new_password": "رمز عبور جدید و تأیید آن مطابقت ندارند"
            })

        token = attrs.get('token')

        try:
            user = CustomUser.objects.get(password_reset_token=token)
        except CustomUser.DoesNotExist:
            raise serializers.ValidationError({"token": "توکن نامعتبر است"})

        if user.password_reset_expires and timezone.now() > user.password_reset_expires:
            raise serializers.ValidationError({"token": "توکن منقضی شده است"})

        attrs['user'] = user
        return attrs


class ChangePasswordSerializer(serializers.Serializer):
    """تغییر رمز عبور"""
    old_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(
        required=True,
        validators=[validate_password],
        write_only=True,
        style={'input_type': 'password'}
    )
    new_password2 = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'}
    )

    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password2']:
            raise serializers.ValidationError({
                "new_password": "رمز عبور جدید و تأیید آن مطابقت ندارند"
            })
        return attrs


class SellerProfileSerializer(serializers.ModelSerializer):
    """سریالایزر پروفایل فروشنده"""
    user = UserSerializer(read_only=True)
    approved_by_username = serializers.CharField(source='approved_by.username', read_only=True)
    assigned_agent_company = serializers.CharField(source='assigned_agent.company_name', read_only=True)

    class Meta:
        model = SellerProfile
        fields = [
            'id', 'user', 'company_name', 'contact_email', 'contact_phone',
            'website', 'address', 'tax_id', 'is_approved', 'approved_by',
            'approved_by_username', 'approved_at', 'rating', 'total_contracts',
            'completed_contracts', 'assigned_agent', 'assigned_agent_company',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'user', 'is_approved', 'approved_by', 'approved_at',
            'rating', 'total_contracts', 'completed_contracts',
            'created_at', 'updated_at'
        ]


class AgentProfileSerializer(serializers.ModelSerializer):
    """سریالایزر پروفایل نماینده"""
    user = UserSerializer(read_only=True)
    approved_by_username = serializers.CharField(source='approved_by.username', read_only=True)
    agent_type_display = serializers.CharField(source='get_agent_type_display', read_only=True)

    class Meta:
        model = AgentProfile
        fields = [
            'id', 'user', 'agent_type', 'agent_type_display', 'company_name',
            'contact_email', 'contact_phone', 'website', 'address',
            'commission_rate', 'is_approved', 'approved_by',
            'approved_by_username', 'approved_at', 'assigned_sellers',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'user', 'is_approved', 'approved_by', 'approved_at',
            'created_at', 'updated_at'
        ]


class AdminProfileSerializer(serializers.ModelSerializer):
    """سریالایزر پروفایل ادمین"""
    user = UserSerializer(read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    role_display = serializers.CharField(source='get_role_display', read_only=True)

    class Meta:
        model = AdminProfile
        fields = [
            'id', 'user', 'role', 'role_display', 'can_manage_users',
            'can_manage_products', 'can_manage_contracts', 'can_manage_settings',
            'created_by', 'created_by_username', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'user', 'created_by', 'created_at', 'updated_at'
        ]


class BuyerProfileSerializer(serializers.ModelSerializer):
    """سریالایزر پروفایل خریدار"""
    user = UserSerializer(read_only=True)
    approved_by_username = serializers.CharField(source='approved_by.username', read_only=True)
    assigned_agent_company = serializers.CharField(source='assigned_agent.company_name', read_only=True)

    class Meta:
        model = BuyerProfile
        fields = [
            'id', 'user', 'amazon_profile_link', 'amazon_reviews_count',
            'amazon_purchases_count', 'address', 'postal_code', 'city',
            'country', 'is_approved', 'approved_by', 'approved_by_username',
            'approved_at', 'assigned_agent', 'assigned_agent_company',
            'total_purchases', 'total_spent', 'success_rate',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'user', 'is_approved', 'approved_by', 'approved_at',
            'total_purchases', 'total_spent', 'success_rate',
            'created_at', 'updated_at'
        ]


class TelegramProfileSerializer(serializers.ModelSerializer):
    """سریالایزر پروفایل تلگرام"""
    user = UserSerializer(read_only=True)

    class Meta:
        model = TelegramProfile
        fields = [
            'id', 'user', 'telegram_id', 'username', 'first_name', 'last_name',
            'language_code', 'is_premium', 'photo_url', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']


class ApproveProfileSerializer(serializers.Serializer):
    """تأیید یا رد پروفایل"""
    is_approved = serializers.BooleanField(required=True)
    reason = serializers.CharField(required=False, allow_blank=True, max_length=500)


class CreateBuyerByAdminSerializer(serializers.Serializer):
    """ایجاد خریدار توسط ادمین/نماینده"""
    telegram_id = serializers.IntegerField(required=True, min_value=1)
    username = serializers.CharField(required=True, max_length=255)
    first_name = serializers.CharField(required=False, allow_blank=True, max_length=255)
    last_name = serializers.CharField(required=False, allow_blank=True, max_length=255)
    assign_to_agent = serializers.IntegerField(required=False, min_value=1)

    def validate_telegram_id(self, value):
        if TelegramProfile.objects.filter(telegram_id=value).exists():
            raise serializers.ValidationError("این آیدی تلگرام قبلاً ثبت شده است")
        return value


class UpdateSellerProfileSerializer(serializers.ModelSerializer):
    """به‌روزرسانی پروفایل فروشنده"""

    class Meta:
        model = SellerProfile
        fields = [
            'company_name', 'contact_email', 'contact_phone',
            'website', 'address', 'tax_id'
        ]
        extra_kwargs = {
            'contact_email': {'required': False},
        }


class UpdateAgentProfileSerializer(serializers.ModelSerializer):
    """به‌روزرسانی پروفایل نماینده"""

    class Meta:
        model = AgentProfile
        fields = [
            'company_name', 'contact_email', 'contact_phone',
            'website', 'address', 'commission_rate'
        ]
        extra_kwargs = {
            'contact_email': {'required': False},
            'commission_rate': {'min_value': 0, 'max_value': 100},
        }


class UpdateBuyerProfileSerializer(serializers.ModelSerializer):
    """به‌روزرسانی پروفایل خریدار"""

    class Meta:
        model = BuyerProfile
        fields = [
            'amazon_profile_link', 'amazon_reviews_count',
            'amazon_purchases_count', 'address', 'postal_code',
            'city', 'country'
        ]
        extra_kwargs = {
            'amazon_reviews_count': {'min_value': 0},
            'amazon_purchases_count': {'min_value': 0},
        }


class AssignSellerSerializer(serializers.Serializer):
    """اختصاص فروشنده به نماینده"""
    seller_id = serializers.IntegerField(required=True, min_value=1)
    agent_id = serializers.IntegerField(required=True, min_value=1)


class UserDetailSerializer(serializers.ModelSerializer):
    """سریالایزر جزئیات کاربر با همه پروفایل‌ها"""
    seller_profile = SellerProfileSerializer(read_only=True)
    agent_profile = AgentProfileSerializer(read_only=True)
    admin_profile = AdminProfileSerializer(read_only=True)
    buyer_profile = BuyerProfileSerializer(read_only=True)
    telegram_profile = TelegramProfileSerializer(read_only=True)

    class Meta:
        model = CustomUser
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'is_verified', 'is_active', 'date_joined', 'created_at',
            'seller_profile', 'agent_profile', 'admin_profile',
            'buyer_profile', 'telegram_profile'
        ]