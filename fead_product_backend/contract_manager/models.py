# contract_manager/models.py
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import uuid


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


class Country(models.Model):
    """مدیریت کامل کشورها"""
    CODE_CHOICES = [
        ('US', 'United States'),
        ('UK', 'United Kingdom'),
        ('DE', 'Germany'),
        ('FR', 'France'),
        ('IT', 'Italy'),
        ('ES', 'Spain'),
        ('IR', 'Iran'),
        ('TR', 'Turkey'),
        ('AE', 'United Arab Emirates'),
        ('SA', 'Saudi Arabia'),
        ('CN', 'China'),
        ('JP', 'Japan'),
        ('KR', 'South Korea'),
        ('IN', 'India'),
        ('BR', 'Brazil'),
        ('CA', 'Canada'),
        ('AU', 'Australia'),
        ('NL', 'Netherlands'),
        ('SE', 'Sweden'),
    ]

    code = models.CharField(max_length=2, choices=CODE_CHOICES, unique=True, verbose_name="Country Code")
    name = models.CharField(max_length=100, verbose_name="Country Name")
    native_name = models.CharField(max_length=100, blank=True, verbose_name="Native Name")

    # آیکون و پرچم
    icon = models.ImageField(
        upload_to=country_icon_upload_path,
        blank=True,
        null=True,
        verbose_name="Country Icon",
        help_text="Small icon for the country"
    )
    flag = models.ImageField(
        upload_to=country_flag_upload_path,
        blank=True,
        null=True,
        verbose_name="Country Flag",
        help_text="National flag of the country"
    )

    # تنظیمات آمازون
    amazon_domain = models.CharField(
        max_length=50,
        default="amazon.com",
        verbose_name="Amazon Domain",
        help_text="e.g., amazon.com, amazon.co.uk, amazon.de"
    )
    amazon_url = models.URLField(
        blank=True,
        verbose_name="Amazon Base URL",
        help_text="Base URL for Amazon in this country"
    )

    # تنظیمات ارز
    default_currency = models.ForeignKey(
        'Currency',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Default Currency",
        help_text="Default currency for this country"
    )

    # تنظیمات منطقه‌ای
    timezone = models.CharField(
        max_length=50,
        default="UTC",
        verbose_name="Timezone",
        help_text="e.g., America/New_York, Europe/London"
    )
    language = models.CharField(
        max_length=10,
        default="en",
        verbose_name="Language Code",
        help_text="e.g., en, de, fr, es"
    )

    # وضعیت
    is_active = models.BooleanField(default=True, verbose_name="Active")
    is_available_for_products = models.BooleanField(default=True, verbose_name="Available for Products")

    # ترتیب نمایش
    display_order = models.IntegerField(default=0, verbose_name="Display Order")

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Country"
        verbose_name_plural = "Countries"
        ordering = ['display_order', 'name']
        db_table = "countries"

    def __str__(self):
        return f"{self.name} ({self.code})"

    def save(self, *args, **kwargs):
        """اتوماتیک کردن Amazon URL اگر خالی باشد"""
        if not self.amazon_url and self.amazon_domain:
            self.amazon_url = f"https://www.{self.amazon_domain}"
        super().save(*args, **kwargs)

    def get_amazon_product_url(self, asin):
        """ایجاد URL محصول آمازون برای این کشور"""
        if self.amazon_domain:
            return f"https://www.{self.amazon_domain}/dp/{asin}"
        return f"https://www.amazon.com/dp/{asin}"

    def get_related_channels(self):
        """دریافت کانال‌های مرتبط با این کشور"""
        from telegram_manager.models import TelegramChannel
        return TelegramChannel.objects.filter(country=self.code, is_active=True)

    def get_primary_channel(self):
        """دریافت کانال اصلی برای این کشور"""
        channels = self.get_related_channels()
        return channels.first()


class CountryChannelConfig(models.Model):
    """تنظیمات کانال‌ها برای هر کشور"""
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
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "Country Channel Configuration"
        verbose_name_plural = "Country Channel Configurations"
        unique_together = ['country', 'channel']
        ordering = ['country', 'priority']
        db_table = "contract_country_channel_config"

    def __str__(self):
        return f"{self.country} - {self.channel.name}"


class Currency(models.Model):
    """مدیریت ارزها و نرخ تبدیل"""
    code = models.CharField(max_length=3, unique=True, verbose_name="Currency Code")  # USD, EUR, CNY
    name = models.CharField(max_length=100, verbose_name="Currency Name")
    exchange_rate_to_cny = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        verbose_name="Exchange Rate to CNY"
    )
    is_active = models.BooleanField(default=True, verbose_name="Active")
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "Currency"
        verbose_name_plural = "Currencies"
        ordering = ['code']
        table_db="currencies"

    def __str__(self):
        return f"{self.code} - {self.name}"


class ActionType(models.Model):
    """انواع اکشن‌های ممکن"""
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

    class Meta:
        verbose_name = "Action Type"
        verbose_name_plural = "Action Types"
        table_db = "contract_action_type"

    def __str__(self):
        return self.get_name_display()


class Seller(models.Model):
    """فروشندگان/نمایندگان"""
    SELLER_TYPES = [
        ('seller', 'Seller'),
        ('agent', 'Agent'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name="User Account")
    seller_type = models.CharField(max_length=10, choices=SELLER_TYPES, verbose_name="Seller Type")
    company_name = models.CharField(max_length=255, verbose_name="Company Name")
    contact_email = models.EmailField(verbose_name="Contact Email")
    contact_phone = models.CharField(max_length=20, blank=True, verbose_name="Contact Phone")
    is_verified = models.BooleanField(default=False, verbose_name="Verified")
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "Seller"
        verbose_name_plural = "Sellers"
        table_db = "contract_seller"

    def __str__(self):
        return f"{self.company_name} ({self.get_seller_type_display()})"


class ContractTemplate(models.Model):
    """تمپلیت قرارداد برای هر سلر"""
    seller = models.ForeignKey(Seller, on_delete=models.CASCADE, verbose_name="Seller")
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
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Contract Template"
        verbose_name_plural = "Contract Templates"
        unique_together = ['seller', 'action_type']
        table_db = "contract_template"

    def __str__(self):
        return f"{self.seller} - {self.action_type}"


# در contract_manager/models.py - آپدیت مدل Product
class Product(models.Model):
    """مدیریت محصولات"""
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

    # 🔥 تغییر از CharField به ForeignKey
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

    # مالکیت
    owner = models.ForeignKey(Seller, on_delete=models.CASCADE, verbose_name="Owner")

    # وضعیت
    is_active = models.BooleanField(default=True, verbose_name="Active")
    is_stopped = models.BooleanField(default=False, verbose_name="Stopped")

    # اطلاعات آمازون
    amazon_product = models.ForeignKey(
        'amazon_app.AmazonProduct',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Amazon Product Data"
    )

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Product"
        verbose_name_plural = "Products"
        ordering = ['-created_at']
        db_table = "contract_product"

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
            amazon_product, message = crawler_service.crawl_amazon_product(self.asin)

            if amazon_product:
                self.amazon_product = amazon_product
                print(f"✅ Successfully crawled Amazon data for {self.asin}: {message}")
            else:
                print(f"❌ Failed to crawl Amazon data for {self.asin}: {message}")

        except Exception as e:
            print(f"❌ Error in _crawl_amazon_data for {self.asin}: {e}")


class ProductContract(models.Model):
    """قراردادهای اختصاصی برای هر محصول"""
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
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "Product Contract"
        verbose_name_plural = "Product Contracts"
        unique_together = ['product', 'contract_template']
        table_db = "contract_product_action_contract"

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




class ProductTelegramMessage(models.Model):
    """مدیریت پیام‌های تلگرام محصولات"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name="Product")
    telegram_message = models.ForeignKey(
        'telegram_manager.TelegramMessage',
        on_delete=models.CASCADE,
        verbose_name="Telegram Message"
    )
    sent_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "Product Telegram Message"
        verbose_name_plural = "Product Telegram Messages"
        table_db = "contract_product_telegram_message"

    def __str__(self):
        return f"{self.product} - {self.telegram_message.telegram_message_id}"
