import datetime

from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.mail import send_mail
from django.conf import settings
import uuid
import secrets


class CustomUser(AbstractUser):
    """کاربر اصلی سیستم - بدون user_type"""

    # ایمیل به عنوان username اصلی
    email = models.EmailField(
        _('email address'),
        unique=True,
        error_messages={
            'unique': _("A user with that email already exists."),
        }
    )

    # تأیید ایمیل
    is_verified = models.BooleanField(default=False, verbose_name="تأیید شده")
    verification_code = models.CharField(max_length=6, blank=True, null=True, verbose_name="کد تأیید")
    verification_code_expires = models.DateTimeField(blank=True, null=True, verbose_name="انقضای کد تأیید")

    # بازیابی رمز عبور
    password_reset_token = models.CharField(max_length=100, blank=True, null=True, verbose_name="توکن بازیابی")
    password_reset_expires = models.DateTimeField(blank=True, null=True, verbose_name="انقضای توکن بازیابی")

    # تاریخ‌ها
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="آخرین به‌روزرسانی")

    class Meta:
        db_table = 'custom_users'
        verbose_name = 'کاربر'
        verbose_name_plural = 'کاربران'
        ordering = ['-date_joined']

    def __str__(self):
        return f"{self.username} ({self.email})"

    def generate_verification_code(self):
        """تولید کد تأیید ۶ رقمی"""
        import random
        code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
        self.verification_code = code
        self.verification_code_expires = timezone.now() + datetime.timedelta(minutes=10)
        self.save()

        # ارسال ایمیل
        try:
            send_mail(
                subject='کد تأیید ثبت نام',
                message=f'کد تأیید شما: {code}\nاین کد تا ۱۰ دقیقه معتبر است.',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[self.email],
                fail_silently=True,
            )
            return code
        except Exception as e:
            print(f"Error sending verification email: {e}")
            return code

    def verify_code(self, code):
        """بررسی کد تأیید"""
        if not self.verification_code:
            return False

        if (self.verification_code == code and
                self.verification_code_expires and
                timezone.now() < self.verification_code_expires):
            self.is_verified = True
            self.verification_code = None
            self.verification_code_expires = None
            self.save()
            return True
        return False

    def generate_password_reset_token(self):
        """تولید توکن ریست پسورد"""
        token = secrets.token_urlsafe(32)
        self.password_reset_token = token
        self.password_reset_expires = timezone.now() + datetime.timedelta(hours=1)
        self.save()

        # ارسال ایمیل با لینک ریست
        try:
            reset_link = f"{settings.FRONTEND_URL}/reset-password/{token}/"
            send_mail(
                subject='بازیابی رمز عبور',
                message=f'برای بازیابی رمز عبور روی لینک زیر کلیک کنید:\n{reset_link}\nاین لینک تا ۱ ساعت معتبر است.',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[self.email],
                fail_silently=True,
            )
            return token
        except Exception as e:
            print(f"Error sending reset email: {e}")
            return token

    def reset_password(self, token, new_password):
        """ریست کردن پسورد با توکن"""
        if (self.password_reset_token == token and
                self.password_reset_expires and
                timezone.now() < self.password_reset_expires):
            self.set_password(new_password)
            self.password_reset_token = None
            self.password_reset_expires = None
            self.save()
            return True
        return False

    @property
    def full_name(self):
        """نام کامل کاربر"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        elif self.last_name:
            return self.last_name
        return self.username

    @property
    def has_admin_profile(self):
        return hasattr(self, 'admin_profile')

    @property
    def has_seller_profile(self):
        return hasattr(self, 'seller_profile')

    @property
    def has_agent_profile(self):
        return hasattr(self, 'agent_profile')

    @property
    def has_buyer_profile(self):
        return hasattr(self, 'buyer_profile')

    @property
    def has_telegram_profile(self):
        return hasattr(self, 'telegram_profile')

    @property
    def is_super_admin(self):
        return self.has_admin_profile and self.admin_profile.role == 'super_admin'

    @property
    def is_admin(self):
        return self.has_admin_profile and self.admin_profile.role == 'admin'

    @property
    def is_approved_seller(self):
        return self.has_seller_profile and self.seller_profile.is_approved

    @property
    def is_approved_agent(self):
        return self.has_agent_profile and self.agent_profile.is_approved

    @property
    def is_internal_agent(self):
        return self.is_approved_agent and self.agent_profile.agent_type == 'internal'

    @property
    def is_external_agent(self):
        return self.is_approved_agent and self.agent_profile.agent_type == 'external'

    # اضافه کردن property برای user_type
    @property
    def user_type(self):
        """نوع کاربر را برمی‌گرداند"""
        if self.has_admin_profile:
            return 'admin'
        elif self.has_seller_profile:
            return 'seller'
        elif self.has_agent_profile:
            return 'agent'
        elif self.has_buyer_profile:
            return 'buyer'
        elif self.has_telegram_profile:
            return 'telegram_user'
        else:
            return 'user'


class TelegramProfile(models.Model):
    """پروفایل تلگرام - فقط برای خریداران"""
    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='telegram_profile',
        verbose_name="کاربر"
    )
    telegram_id = models.BigIntegerField(unique=True, verbose_name="آیدی تلگرام")
    username = models.CharField(max_length=255, blank=True, null=True, verbose_name="نام کاربری تلگرام")
    first_name = models.CharField(max_length=255, blank=True, null=True, verbose_name="نام")
    last_name = models.CharField(max_length=255, blank=True, null=True, verbose_name="نام خانوادگی")
    language_code = models.CharField(max_length=10, blank=True, null=True, verbose_name="کد زبان")
    is_premium = models.BooleanField(default=False, verbose_name="پریمیوم")
    photo_url = models.URLField(max_length=500, blank=True, null=True, verbose_name="آدرس عکس")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="آخرین به‌روزرسانی")

    class Meta:
        db_table = 'telegram_profiles'
        verbose_name = 'پروفایل تلگرام'
        verbose_name_plural = 'پروفایل‌های تلگرام'

    def __str__(self):
        return f"{self.user.username} (Telegram ID: {self.telegram_id})"


class AdminProfile(models.Model):
    """پروفایل ادمین - فقط توسط سوپر ادمین ایجاد می‌شود"""

    ROLE_CHOICES = [
        ('super_admin', 'سوپر ادمین'),
        ('admin', 'ادمین'),
    ]

    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='admin_profile',
        verbose_name="کاربر"
    )
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='admin',
        verbose_name="نقش"
    )

    # دسترسی‌ها
    can_manage_users = models.BooleanField(default=True, verbose_name="مدیریت کاربران")
    can_manage_products = models.BooleanField(default=True, verbose_name="مدیریت محصولات")
    can_manage_contracts = models.BooleanField(default=True, verbose_name="مدیریت قراردادها")
    can_manage_settings = models.BooleanField(default=False, verbose_name="مدیریت تنظیمات")

    created_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_admins',
        verbose_name="ایجاد شده توسط"
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="آخرین به‌روزرسانی")

    class Meta:
        db_table = 'admin_profiles'
        verbose_name = 'پروفایل ادمین'
        verbose_name_plural = 'پروفایل‌های ادمین'

    def __str__(self):
        return f"{self.get_role_display()}: {self.user.username}"


class SellerProfile(models.Model):
    """پروفایل فروشنده"""

    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='seller_profile',
        verbose_name="کاربر"
    )

    # اطلاعات شرکت
    company_name = models.CharField(max_length=255, verbose_name="نام شرکت")
    contact_email = models.EmailField(verbose_name="ایمیل تماس")
    contact_phone = models.CharField(max_length=20, verbose_name="تلفن تماس")
    website = models.URLField(blank=True, null=True, verbose_name="وبسایت")
    address = models.TextField(blank=True, null=True, verbose_name="آدرس")
    tax_id = models.CharField(max_length=100, blank=True, null=True, verbose_name="شناسه مالیاتی")

    # نماینده اختصاصی - تغییر related_name
    assigned_agent = models.ForeignKey(
        'AgentProfile',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_sellers_profiles',  # تغییر نام برای جلوگیری از clash
        verbose_name="نماینده اختصاصی"
    )

    # وضعیت تأیید توسط ادمین
    is_approved = models.BooleanField(default=False, verbose_name="تأیید شده")
    approved_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_sellers',
        verbose_name="تأیید کننده"
    )
    approved_at = models.DateTimeField(null=True, blank=True, verbose_name="زمان تأیید")

    # امتیاز و رتبه
    rating = models.FloatField(default=0.0, verbose_name="امتیاز")
    total_contracts = models.IntegerField(default=0, verbose_name="تعداد قراردادها")
    completed_contracts = models.IntegerField(default=0, verbose_name="قراردادهای تکمیل شده")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="آخرین به‌روزرسانی")

    class Meta:
        db_table = 'seller_profiles'
        verbose_name = 'پروفایل فروشنده'
        verbose_name_plural = 'پروفایل‌های فروشنده'

    def __str__(self):
        return f"فروشنده: {self.company_name} ({self.user.username})"

    def approve(self, admin_user):
        """تأیید فروشنده توسط ادمین"""
        self.is_approved = True
        self.approved_by = admin_user
        self.approved_at = timezone.now()
        self.save()

    def disapprove(self):
        """لغو تأیید فروشنده"""
        self.is_approved = False
        self.approved_by = None
        self.approved_at = None
        self.save()


class AgentProfile(models.Model):
    """پروفایل نماینده"""

    AGENT_TYPES = [
        ('internal', 'نماینده داخلی'),
        ('external', 'نماینده خارجی'),
    ]

    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='agent_profile',
        verbose_name="کاربر"
    )

    agent_type = models.CharField(
        max_length=10,
        choices=AGENT_TYPES,
        default='external',
        verbose_name="نوع نماینده"
    )

    # اطلاعات شرکت
    company_name = models.CharField(max_length=255, verbose_name="نام شرکت/نماینده")
    contact_email = models.EmailField(verbose_name="ایمیل تماس")
    contact_phone = models.CharField(max_length=20, verbose_name="تلفن تماس")
    website = models.URLField(blank=True, null=True, verbose_name="وبسایت")
    address = models.TextField(blank=True, null=True, verbose_name="آدرس")

    # وضعیت تأیید توسط ادمین
    is_approved = models.BooleanField(default=False, verbose_name="تأیید شده")
    approved_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_agents',
        verbose_name="تأیید کننده"
    )
    approved_at = models.DateTimeField(null=True, blank=True, verbose_name="زمان تأیید")

    # کمیسیون
    commission_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=10.00,
        verbose_name="نرخ کمیسیون (%)"
    )

    # فروشندگان اختصاص‌یافته - تغییر نام فیلد
    managed_sellers = models.ManyToManyField(  # تغییر نام از assigned_sellers به managed_sellers
        SellerProfile,
        blank=True,
        related_name='managed_by_agents',  # تغییر related_name
        verbose_name="فروشندگان تحت مدیریت"
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="آخرین به‌روزرسانی")

    class Meta:
        db_table = 'agent_profiles'
        verbose_name = 'پروفایل نماینده'
        verbose_name_plural = 'پروفایل‌های نماینده'

    def __str__(self):
        return f"نماینده: {self.company_name} ({self.get_agent_type_display()})"

    def approve(self, admin_user):
        """تأیید نماینده توسط ادمین"""
        self.is_approved = True
        self.approved_by = admin_user
        self.approved_at = timezone.now()
        self.save()

    def disapprove(self):
        """لغو تأیید نماینده"""
        self.is_approved = False
        self.approved_by = None
        self.approved_at = None
        self.save()

    # اضافه کردن property برای total_buyers
    @property
    def total_buyers(self):
        """تعداد خریداران تحت مدیریت این نماینده"""
        return self.assigned_buyers.count()


class BuyerProfile(models.Model):
    """پروفایل خریدار"""

    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='buyer_profile',
        verbose_name="کاربر"
    )

    # اطلاعات آمازون
    amazon_profile_link = models.URLField(max_length=500, blank=True, null=True, verbose_name="لینک پروفایل آمازون")
    amazon_reviews_count = models.IntegerField(default=0, verbose_name="تعداد ریویوهای آمازون")
    amazon_purchases_count = models.IntegerField(default=0, verbose_name="تعداد خریدهای آمازون")

    # اطلاعات شخصی
    address = models.TextField(blank=True, null=True, verbose_name="آدرس")
    postal_code = models.CharField(max_length=20, blank=True, null=True, verbose_name="کد پستی")
    city = models.CharField(max_length=100, blank=True, null=True, verbose_name="شهر")
    country = models.CharField(max_length=100, blank=True, null=True, verbose_name="کشور")

    # وابستگی به نماینده
    assigned_agent = models.ForeignKey(
        AgentProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_buyers',
        verbose_name="نماینده اختصاصی"
    )

    # وضعیت تأیید توسط ادمین/نماینده
    is_approved = models.BooleanField(default=False, verbose_name="تأیید شده")
    approved_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_buyers',
        verbose_name="تأیید کننده"
    )
    approved_at = models.DateTimeField(null=True, blank=True, verbose_name="زمان تأیید")

    # آمار
    total_purchases = models.IntegerField(default=0, verbose_name="تعداد خریدها")
    total_spent = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        verbose_name="مجموع هزینه‌ها"
    )
    success_rate = models.FloatField(default=0.0, verbose_name="نرخ موفقیت")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="آخرین به‌روزرسانی")

    class Meta:
        db_table = 'buyer_profiles'
        verbose_name = 'پروفایل خریدار'
        verbose_name_plural = 'پروفایل‌های خریدار'

    def __str__(self):
        return f"خریدار: {self.user.username}"

    def approve(self, approver):
        """تأیید خریدار توسط ادمین یا نماینده"""
        self.is_approved = True
        self.approved_by = approver
        self.approved_at = timezone.now()
        self.save()

    def disapprove(self):
        """لغو تأیید خریدار"""
        self.is_approved = False
        self.approved_by = None
        self.approved_at = None
        self.save()
