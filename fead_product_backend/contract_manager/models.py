from django.db import models
from auth_app.models import SellerProfile, AgentProfile, AdminProfile, CustomUser
from django.conf import settings
from django.utils import timezone
import uuid
import os


def country_icon_upload_path(instance, filename):
    """مسیر آپلود آیکون کشور"""
    ext = filename.split('.')[-1]
    filename = f"{instance.code}.{ext}"
    return f'countries/icons/{filename}'

def country_flag_upload_path(instance, filename):
    """مسیر آپلود پرچم کشور"""
    ext = filename.split('.')[-1]
    filename = f"{instance.code}_flag.{ext}"
    return f'countries/flags/{filename}'


class Currency(models.Model):
    """مدیریت ارزها و نرخ تبدیل"""
    class Meta:
        app_label = 'contract_manager'
        verbose_name = "Currency"
        verbose_name_plural = "Currencies"
        ordering = ['code']
        db_table = "currencies"

    code = models.CharField(max_length=3, unique=True, verbose_name="Currency Code", primary_key=True)
    name = models.CharField(max_length=100, verbose_name="Currency Name")
    exchange_rate_to_cny = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        verbose_name="Exchange Rate to CNY"
    )
    symbol = models.CharField(max_length=5, blank=True, verbose_name="Symbol")
    is_active = models.BooleanField(default=True, verbose_name="Active")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.code} - {self.name}"


class Country(models.Model):
    """مدیریت کامل کشورها"""
    class Meta:
        app_label = 'contract_manager'
        verbose_name = "Country"
        verbose_name_plural = "Countries"
        ordering = ['display_order', 'name']
        db_table = "countries"

    CODE_CHOICES = [
        ('US', 'United States'), ('UK', 'United Kingdom'), ('DE', 'Germany'),
        ('FR', 'France'), ('IT', 'Italy'), ('ES', 'Spain'), ('IR', 'Iran'),
        ('TR', 'Turkey'), ('AE', 'United Arab Emirates'), ('SA', 'Saudi Arabia'),
        ('CN', 'China'), ('JP', 'Japan'), ('KR', 'South Korea'), ('IN', 'India'),
        ('BR', 'Brazil'), ('CA', 'Canada'), ('AU', 'Australia'), ('NL', 'Netherlands'),
        ('SE', 'Sweden'),
    ]

    # اطلاعات پایه
    code = models.CharField(max_length=2, choices=CODE_CHOICES, unique=True, verbose_name="Country Code", primary_key=True)
    name = models.CharField(max_length=100, verbose_name="Country Name")
    native_name = models.CharField(max_length=100, blank=True, verbose_name="Native Name")

    # رسانه
    icon = models.ImageField(
        upload_to=country_icon_upload_path,
        blank=True, null=True,
        verbose_name="Country Icon",
        help_text="آیکون کوچک برای کشور"
    )
    flag = models.ImageField(
        upload_to=country_flag_upload_path,
        blank=True, null=True,
        verbose_name="Country Flag",
        help_text="پرچم ملی کشور"
    )

    # تنظیمات آمازون
    amazon_domain = models.CharField(
        max_length=50,
        default="amazon.com",
        verbose_name="Amazon Domain",
        help_text="مثال: amazon.com, amazon.co.uk, amazon.de"
    )
    amazon_url = models.URLField(
        blank=True,
        verbose_name="Amazon Base URL",
        help_text="URL پایه آمازون در این کشور"
    )

    # تنظیمات منطقه‌ای
    default_currency = models.ForeignKey(
        Currency,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name="Default Currency",
        help_text="ارز پیش‌فرض برای این کشور"
    )
    timezone = models.CharField(
        max_length=50,
        default="UTC",
        verbose_name="Timezone",
        help_text="مثال: America/New_York, Europe/London"
    )
    language = models.CharField(
        max_length=10,
        default="en",
        verbose_name="Language Code",
        help_text="مثال: en, de, fr, es"
    )

    # موقعیت جغرافیایی پیش‌فرض برای کراولینگ
    default_zip_code = models.CharField(max_length=20, blank=True, verbose_name="Default ZIP Code")
    default_city = models.CharField(max_length=100, blank=True, verbose_name="Default City")
    default_state = models.CharField(max_length=100, blank=True, verbose_name="Default State")

    # وضعیت
    is_active = models.BooleanField(default=True, verbose_name="Active")
    is_available_for_products = models.BooleanField(default=True, verbose_name="Available for Products")
    is_available_for_crawling = models.BooleanField(default=True, verbose_name="Available for Crawling")
    display_order = models.IntegerField(default=0, verbose_name="Display Order")

    # زمان‌ها
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True, null=True)

    def __str__(self):
        return f"{self.name} ({self.code})"

    def save(self, *args, **kwargs):
        if not self.amazon_url and self.amazon_domain:
            self.amazon_url = f"https://www.{self.amazon_domain}"
        super().save(*args, **kwargs)

    def get_amazon_product_url(self, asin):
        if self.amazon_domain:
            return f"https://www.{self.amazon_domain}/dp/{asin}"
        return f"https://www.amazon.com/dp/{asin}"

    def get_related_channels(self):
        from telegram_manager.models import TelegramChannel
        try:
            return TelegramChannel.objects.filter(country=self.code, is_active=True)
        except ImportError:
            return TelegramChannel.objects.none()

    def get_primary_channel(self):
        channels = self.get_related_channels()
        return channels.first()

    def get_currency_code(self):
        if self.default_currency:
            return self.default_currency.code
        currency_map = {
            'US': 'USD', 'UK': 'GBP', 'DE': 'EUR', 'FR': 'EUR', 'IT': 'EUR',
            'ES': 'EUR', 'CA': 'CAD', 'AU': 'AUD', 'JP': 'JPY', 'IN': 'INR',
            'BR': 'BRL', 'TR': 'TRY', 'AE': 'AED', 'SA': 'SAR', 'CN': 'CNY',
            'KR': 'KRW', 'NL': 'EUR', 'SE': 'SEK', 'IR': 'IRR'
        }
        return currency_map.get(self.code, 'USD')

    @classmethod
    def get_amazon_countries(cls):
        """دریافت کشورهایی که Amazon در آنها فعال است"""
        # کشورهایی که به طور پیش‌فرض Amazon دارند
        amazon_country_codes = [
            'US', 'UK', 'DE', 'FR', 'IT', 'ES', 'CA', 'AU',
            'JP', 'IN', 'BR', 'MX', 'NL', 'SE', 'PL', 'SG',
            'AE', 'SA', 'TR', 'CN'
        ]

        return cls.objects.filter(
            code__in=amazon_country_codes,
            is_active=True,
            is_available_for_crawling=True
        )

    # اضافه کردن متد برای آیکون و پرچم (اختیاری)
    def get_icon_url(self):
        """دریافت URL آیکون کشور"""
        if self.icon:
            return self.icon.url
        return None

    def get_flag_url(self):
        """دریافت URL پرچم کشور"""
        if self.flag:
            return self.flag.url
        return None

    @property
    def has_amazon(self):
        """بررسی اینکه آیا این کشور Amazon دارد"""
        amazon_domains = [
            'amazon.com', 'amazon.co.uk', 'amazon.de', 'amazon.fr',
            'amazon.it', 'amazon.es', 'amazon.ca', 'amazon.com.au',
            'amazon.co.jp', 'amazon.in', 'amazon.com.br', 'amazon.com.mx',
            'amazon.nl', 'amazon.se', 'amazon.pl', 'amazon.sg',
            'amazon.ae', 'amazon.sa', 'amazon.com.tr', 'amazon.cn'
        ]
        return any(domain in self.amazon_domain for domain in amazon_domains)


class CountryChannelConfig(models.Model):
    """تنظیمات کانال‌ها برای هر کشور"""

    class Meta:
        app_label = 'contract_manager'
        verbose_name = "Country Channel Configuration"
        verbose_name_plural = "Country Channel Configurations"
        unique_together = ['country', 'channel']
        ordering = ['country', 'priority']
        db_table = "contract_country_channel_config"

    country = models.ForeignKey(Country, on_delete=models.CASCADE, verbose_name="Country")
    channel = models.ForeignKey(
        'telegram_manager.TelegramChannel',
        on_delete=models.CASCADE,
        verbose_name="Telegram Channel"
    )
    is_primary = models.BooleanField(default=False, verbose_name="Primary Channel")
    priority = models.IntegerField(default=1, verbose_name="Priority", help_text="Lower number = higher priority")

    # تنظیمات ارسال
    auto_send_new_products = models.BooleanField(default=True, verbose_name="Auto Send New Products")
    send_product_updates = models.BooleanField(default=True, verbose_name="Send Product Updates")
    send_price_alerts = models.BooleanField(default=False, verbose_name="Send Price Alerts")

    # قالب پیام
    message_template = models.TextField(
        blank=True,
        verbose_name="Custom Message Template",
        help_text="Custom template for product messages. Use {{variable}} for placeholders."
    )

    is_active = models.BooleanField(default=True, verbose_name="Active")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.country} - {self.channel.name}"


class ActionType(models.Model):
    """انواع اکشن‌های ممکن"""
    class Meta:
        app_label = 'contract_manager'
        verbose_name = "Action Type"
        verbose_name_plural = "Action Types"
        db_table = "contract_action_type"

    ACTION_CHOICES = [
        ('review', 'Register Review'),
        ('rating_5', 'Register 5-Star Rating'),
        ('rating_4_plus', 'Register 4+ Star Rating'),
        ('photo', 'Register Photo'),
        ('video', 'Register Video'),
        ('seller_feedback', 'Register Seller Feedback'),
    ]

    name = models.CharField(max_length=50, choices=ACTION_CHOICES, unique=True, verbose_name="Action Name")
    description = models.TextField(blank=True, verbose_name="Description")
    is_active = models.BooleanField(default=True, verbose_name="Active")

    def __str__(self):
        return self.get_name_display()


class ContractTemplate(models.Model):
    """تمپلیت قرارداد برای هر سلر"""
    class Meta:
        app_label = 'contract_manager'
        verbose_name = "Contract Template"
        verbose_name_plural = "Contract Templates"
        unique_together = ['seller', 'action_type']
        db_table = "contract_template"

    # تغییر به SellerProfile از auth_app
    seller = models.ForeignKey(
        SellerProfile,
        on_delete=models.CASCADE,
        verbose_name="Seller"
    )
    action_type = models.ForeignKey(ActionType, on_delete=models.CASCADE, verbose_name="Action Type")
    refund_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        verbose_name="Refund Percentage",
        help_text="Percentage of product price to refund"
    )
    commission_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Commission Amount"
    )
    commission_currency = models.ForeignKey(
        Currency,
        on_delete=models.CASCADE,
        verbose_name="Commission Currency"
    )
    refund_description = models.TextField(verbose_name="Refund Description")
    is_active = models.BooleanField(default=True, verbose_name="Active")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.seller} - {self.action_type}"


class Product(models.Model):
    """مدیریت محصولات"""
    class Meta:
        app_label = 'contract_manager'
        verbose_name = "Product"
        verbose_name_plural = "Products"
        ordering = ['-created_at']
        db_table = "contract_product"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    asin = models.CharField(max_length=10, unique=True, verbose_name="ASIN")
    variant_asins = models.TextField(
        blank=True,
        verbose_name="Variant ASINs",
        help_text="Comma-separated list of variant ASINs"
    )
    title = models.CharField(max_length=500, verbose_name="Product Title")
    description = models.TextField(blank=True, verbose_name="Description")
    search_guide = models.TextField(blank=True, verbose_name="Search Guide")
    product_url = models.URLField(verbose_name="Product URL")

    # کشور محصول
    country = models.ForeignKey(
        Country,
        on_delete=models.CASCADE,
        verbose_name="Country",
        limit_choices_to={'is_available_for_products': True}
    )

    # محدودیت‌ها
    daily_max_quantity = models.IntegerField(default=10, verbose_name="Daily Max Quantity")
    total_max_quantity = models.IntegerField(default=100, verbose_name="Total Max Quantity")
    current_quantity = models.IntegerField(default=0, verbose_name="Current Quantity")

    # مالکیت - تغییر به SellerProfile
    owner = models.ForeignKey(
        SellerProfile,
        on_delete=models.CASCADE,
        verbose_name="Owner"
    )

    # وضعیت
    is_active = models.BooleanField(default=True, verbose_name="Active")
    is_stopped = models.BooleanField(default=False, verbose_name="Stopped")

    # اطلاعات آمازون
    amazon_product = models.ForeignKey(
        'amazon_app.AmazonProduct',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name="Amazon Product Data"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} ({self.asin}) - {self.country.name}"

    def get_variant_asins_list(self):
        """تبدیل variant ASINs به لیست"""
        if self.variant_asins:
            return [asin.strip() for asin in self.variant_asins.split(',')]
        return []

    def get_related_channels(self):
        """دریافت کانال‌های مرتبط با کشور محصول"""
        return self.country.get_related_channels()

    def get_primary_channel(self):
        """دریافت کانال اصلی برای کشور محصول"""
        return self.country.get_primary_channel()

    def get_amazon_url(self):
        """دریافت URL محصول در آمازون مربوطه"""
        return self.country.get_amazon_product_url(self.asin)

    def create_or_update_telegram_message(self, channel, message_text: str, images: list = None):
        """ایجاد یا بروزرسانی پیام تلگرام برای محصول در یک کانال"""
        from .models import ProductChannel
        product_channel, created = ProductChannel.objects.get_or_create(
            product=self,
            channel=channel,
            defaults={
                'telegram_message_text': message_text,
                'telegram_images': images or [],
                'status': 'draft',
            }
        )

        if not created:
            product_channel.telegram_message_text = message_text
            product_channel.telegram_images = images or []
            if product_channel.status == 'sent':
                product_channel.status = 'edited'
            product_channel.save()

        return product_channel

    def get_telegram_messages(self):
        """دریافت تمام پیام‌های تلگرام محصول"""
        return ProductChannel.objects.filter(product=self)

    def stop_all_messages(self):
        """متوقف کردن همه پیام‌های محصول"""
        messages = self.get_telegram_messages().filter(status='sent')
        for msg in messages:
            msg.mark_as_stopped()
        self.is_stopped = True
        self.save()

    def resume_all_messages(self):
        """ادامه دادن همه پیام‌های متوقف شده"""
        messages = self.get_telegram_messages().filter(status='stopped')
        for msg in messages:
            msg.status = 'sent'
            msg.save()
        self.is_stopped = False
        self.save()

    def save(self, *args, **kwargs):
        """اتوماتیک کراول کردن وقتی محصول جدید ایجاد میشه"""
        is_new = self._state.adding

        if is_new and not self.amazon_product:
            # اگر محصول جدیده و amazon_product نداره، کراول کن
            self._crawl_amazon_data()

        super().save(*args, **kwargs)

    def _crawl_amazon_data(self):
        """کراول کردن داده‌های آمازون با استفاده از سرویس اختصاصی"""
        try:
            from .services import ProductCrawlerService

            crawler_service = ProductCrawlerService()

            # استفاده از سرویس یکپارچه
            amazon_product, message = crawler_service.crawl_amazon_product(
                self.asin,
                self.country.code
            )

            if amazon_product:
                self.amazon_product = amazon_product
                print(f"✅ Successfully crawled Amazon data for {self.asin}: {message}")
            else:
                print(f"❌ Failed to crawl Amazon data for {self.asin}: {message}")

        except Exception as e:
            print(f"❌ Error in _crawl_amazon_data for {self.asin}: {e}")


class ProductContract(models.Model):
    """قراردادهای اختصاصی برای هر محصول"""

    class Meta:
        app_label = 'contract_manager'
        verbose_name = "Product Contract"
        verbose_name_plural = "Product Contracts"
        unique_together = ['product', 'contract_template']
        db_table = "contract_product_action_contract"

    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name="Product")
    contract_template = models.ForeignKey(ContractTemplate, on_delete=models.CASCADE, verbose_name="Contract Template")
    custom_refund_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Custom Refund Percentage"
    )
    custom_commission_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Custom Commission Amount"
    )
    is_active = models.BooleanField(default=True, verbose_name="Active")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.product} - {self.contract_template}"

    def get_effective_refund_percentage(self):
        """درصد ریفاند مؤثر"""
        return float(self.custom_refund_percentage) if self.custom_refund_percentage else float(
            self.contract_template.refund_percentage)

    def get_effective_commission(self):
        """کمیسیون مؤثر"""
        return float(self.custom_commission_amount) if self.custom_commission_amount else float(
            self.contract_template.commission_amount)


class ProductChannel(models.Model):
    """مدیریت ارسال محصول به کانال‌های خاص"""

    class Meta:
        app_label = 'contract_manager'
        verbose_name = "Product Channel"
        verbose_name_plural = "Product Channels"
        unique_together = ['product', 'channel']
        ordering = ['-sent_at']
        db_table = "contract_product_channel"

    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('edited', 'Edited'),
        ('deleted', 'Deleted'),
        ('failed', 'Failed'),
        ('stopped', 'Stopped'),
    ]

    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name="Product")
    channel = models.ForeignKey(
        'telegram_manager.TelegramChannel',
        on_delete=models.CASCADE,
        verbose_name="Telegram Channel"
    )

    # اطلاعات پیام تلگرام
    telegram_message_id = models.CharField(max_length=100, blank=True, null=True, verbose_name="Telegram Message ID")
    telegram_message_text = models.TextField(verbose_name="Telegram Message Text")
    telegram_images = models.JSONField(default=list, verbose_name="Telegram Images", help_text="لیست URL عکس‌ها")

    # وضعیت و زمان‌بندی
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft', verbose_name="Status")
    should_send = models.BooleanField(default=True, verbose_name="Should Send to Channel")
    sent_at = models.DateTimeField(null=True, blank=True, verbose_name="Sent At")
    edited_at = models.DateTimeField(null=True, blank=True, verbose_name="Edited At")
    deleted_at = models.DateTimeField(null=True, blank=True, verbose_name="Deleted At")

    # آمار و لاگ
    view_count = models.IntegerField(default=0, verbose_name="View Count")
    click_count = models.IntegerField(default=0, verbose_name="Click Count")
    error_log = models.TextField(blank=True, verbose_name="Error Log")

    # تنظیمات
    auto_update = models.BooleanField(default=True, verbose_name="Auto Update Message")
    notify_on_change = models.BooleanField(default=True, verbose_name="Notify on Product Change")

    # زمان‌ها
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.product.asin} -> {self.channel.name} ({self.status})"

    def is_sent(self):
        return self.status == 'sent' and self.telegram_message_id is not None

    def can_edit(self):
        return self.is_sent() and self.status not in ['deleted', 'stopped']

    def can_delete(self):
        return self.is_sent() and self.status not in ['deleted']

    def mark_as_sent(self, telegram_message_id: str):
        self.status = 'sent'
        self.telegram_message_id = telegram_message_id
        self.sent_at = timezone.now()
        self.save()

    def mark_as_edited(self):
        self.status = 'edited'
        self.edited_at = timezone.now()
        self.save()

    def mark_as_deleted(self):
        self.status = 'deleted'
        self.deleted_at = timezone.now()
        self.save()

    def mark_as_stopped(self):
        self.status = 'stopped'
        self.save()

    def update_statistics(self, views=None, clicks=None):
        if views is not None:
            self.view_count = views
        if clicks is not None:
            self.click_count = clicks
        self.save()

    def get_message_data(self):
        """دریافت داده‌های پیام برای ارسال"""
        return {
            'message_text': self.telegram_message_text,
            'images': self.telegram_images,
            'product_asin': self.product.asin,
            'product_title': self.product.title,
            'country_code': self.product.country.code,
        }


class ProductUpdateLog(models.Model):
    """لاگ تغییرات محصول"""

    class Meta:
        app_label = 'contract_manager'
        verbose_name = "Product Update Log"
        verbose_name_plural = "Product Update Logs"
        ordering = ['-created_at']
        db_table = "contract_product_update_log"

    UPDATE_TYPES = [
        ('price_change', 'Price Change'),
        ('stock_change', 'Stock Change'),
        ('info_update', 'Information Update'),
        ('status_change', 'Status Change'),
        ('telegram_update', 'Telegram Message Update'),
        ('channel_update', 'Channel Status Update'),
    ]

    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name="Product")
    update_type = models.CharField(max_length=50, choices=UPDATE_TYPES, verbose_name="Update Type")
    old_data = models.JSONField(default=dict, verbose_name="Old Data")
    new_data = models.JSONField(default=dict, verbose_name="New Data")
    description = models.TextField(blank=True, verbose_name="Description")

    # تاثیر بر کانال‌ها
    affected_channels = models.JSONField(default=list, verbose_name="Affected Channels")
    telegram_updates_sent = models.BooleanField(default=False, verbose_name="Telegram Updates Sent")

    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Created By")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.product.asin} - {self.get_update_type_display()} at {self.created_at}"