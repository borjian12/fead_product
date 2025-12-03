# amazon_app/models.py
from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator


class AmazonProduct(models.Model):
    CONDITION_CHOICES = [
        ('NEW', 'New'),
        ('USED', 'Used'),
        ('RENEWED', 'Renewed'),
        ('REFURBISHED', 'Refurbished'),
    ]

    COUNTRY_CHOICES = [
        ('US', 'United States'),
        ('UK', 'United Kingdom'),
        ('DE', 'Germany'),
        ('FR', 'France'),
        ('IT', 'Italy'),
        ('ES', 'Spain'),
        ('CA', 'Canada'),
        ('JP', 'Japan'),
        ('AU', 'Australia'),
    ]

    asin = models.CharField(max_length=10, verbose_name="ASIN")
    country_code = models.CharField(max_length=2, choices=COUNTRY_CHOICES, default='US', verbose_name="Country Code")
    title = models.TextField(verbose_name="Product Title")
    description = models.TextField(blank=True, verbose_name="Description")
    brand = models.CharField(max_length=200, blank=True, verbose_name="Brand")
    manufacturer = models.CharField(max_length=200, blank=True, verbose_name="Manufacturer")
    category = models.CharField(max_length=200, blank=True, verbose_name="Category")
    image_url = models.URLField(max_length=500, blank=True, verbose_name="Image URL")
    product_url = models.URLField(max_length=500, blank=True, verbose_name="Product URL")
    condition = models.CharField(max_length=20, choices=CONDITION_CHOICES, default='NEW', verbose_name="Condition")
    features = models.JSONField(default=list, blank=True, verbose_name="Features")
    specifications = models.JSONField(default=dict, blank=True, verbose_name="Specifications")
    rating = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True, verbose_name="Rating")
    review_count = models.IntegerField(default=0, verbose_name="Review Count")
    variants = models.JSONField(default=list, blank=True, verbose_name="Variants")
    domain = models.CharField(max_length=50, default="amazon.com", verbose_name="Amazon Domain")
    geo_location = models.JSONField(default=dict, blank=True, verbose_name="Geo Location")

    # 🔥 اضافه کردن فیلدهای فروشنده
    seller = models.CharField(max_length=200, blank=True, verbose_name="Seller")
    seller_id = models.CharField(max_length=50, blank=True, verbose_name="Seller ID")
    seller_type = models.CharField(max_length=50, blank=True, verbose_name="Seller Type")
    seller_info = models.JSONField(default=dict, blank=True, verbose_name="Seller Information")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated At")
    last_crawled = models.DateTimeField(null=True, blank=True, verbose_name="Last Crawled")
    is_active = models.BooleanField(default=True, verbose_name="Is Active")

    class Meta:
        db_table = 'amazon_products'
        indexes = [
            models.Index(fields=['asin', 'country_code']),
            models.Index(fields=['country_code']),
            models.Index(fields=['brand']),
            models.Index(fields=['category']),
            models.Index(fields=['rating']),
            models.Index(fields=['seller']),  # 🔥 اضافه کردن ایندکس برای فروشنده
        ]
        ordering = ['-created_at']
        unique_together = ['asin', 'country_code']

    def __str__(self):
        return f"{self.asin} - {self.get_country_code_display()} - {self.title[:50]}"

    def get_amazon_url(self):
        return f"https://www.{self.domain}/dp/{self.asin}"

class AmazonProductPrice(models.Model):
    CURRENCY_CHOICES = [
        ('USD', 'US Dollar'),
        ('EUR', 'Euro'),
        ('GBP', 'British Pound'),
        ('CAD', 'Canadian Dollar'),
        ('AUD', 'Australian Dollar'),
        ('JPY', 'Japanese Yen'),
    ]

    COUNTRY_CHOICES = [
        ('US', 'United States'),
        ('UK', 'United Kingdom'),
        ('DE', 'Germany'),
        ('FR', 'France'),
        ('IT', 'Italy'),
        ('ES', 'Spain'),
        ('CA', 'Canada'),
        ('JP', 'Japan'),
        ('AU', 'Australia'),
    ]

    product = models.ForeignKey(AmazonProduct, on_delete=models.CASCADE, related_name='prices', verbose_name="Product")
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)], verbose_name="Price")
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default='USD', verbose_name="Currency")
    country_code = models.CharField(max_length=2, choices=COUNTRY_CHOICES, default='US', verbose_name="Country Code")
    seller = models.CharField(max_length=200, blank=True, verbose_name="Seller")
    seller_type = models.CharField(max_length=50, blank=True, verbose_name="Seller Type")
    availability = models.BooleanField(default=True, verbose_name="Availability")
    stock_status = models.CharField(max_length=100, blank=True, verbose_name="Stock Status")
    shipping_info = models.TextField(blank=True, verbose_name="Shipping Info")
    delivery_date = models.CharField(max_length=100, blank=True, verbose_name="Delivery Date")
    crawl_source = models.CharField(max_length=100, verbose_name="Crawl Source")
    crawl_timestamp = models.DateTimeField(default=timezone.now, verbose_name="Crawl Timestamp")
    metadata = models.JSONField(default=dict, blank=True, verbose_name="Metadata")

    class Meta:
        db_table = 'amazon_product_prices'
        indexes = [
            models.Index(fields=['product', 'crawl_timestamp']),
            models.Index(fields=['country_code', 'crawl_timestamp']),
            models.Index(fields=['crawl_timestamp']),
            models.Index(fields=['price']),
        ]
        ordering = ['-crawl_timestamp']

    def __str__(self):
        return f"{self.product.asin} - {self.country_code} - ${self.price} - {self.crawl_timestamp.strftime('%Y-%m-%d %H:%M')}"

class AmazonCrawlSession(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('RUNNING', 'Running'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
        ('PARTIAL', 'Partial Success'),
    ]

    COUNTRY_CHOICES = [
        ('US', 'United States'),
        ('UK', 'United Kingdom'),
        ('DE', 'Germany'),
        ('FR', 'France'),
        ('IT', 'Italy'),
        ('ES', 'Spain'),
        ('CA', 'Canada'),
        ('JP', 'Japan'),
        ('AU', 'Australia'),
    ]

    session_id = models.CharField(max_length=100, unique=True, verbose_name="Session ID")
    driver_name = models.CharField(max_length=100, verbose_name="Driver Name")
    country_code = models.CharField(max_length=2, choices=COUNTRY_CHOICES, default='US', verbose_name="Country Code")
    asins_crawled = models.JSONField(default=list, verbose_name="ASINs Crawled")
    total_products = models.IntegerField(default=0, verbose_name="Total Products")
    successful_crawls = models.IntegerField(default=0, verbose_name="Successful Crawls")
    failed_crawls = models.IntegerField(default=0, verbose_name="Failed Crawls")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING', verbose_name="Status")
    started_at = models.DateTimeField(auto_now_add=True, verbose_name="Started At")
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name="Completed At")
    error_log = models.TextField(blank=True, verbose_name="Error Log")

    class Meta:
        db_table = 'amazon_crawl_sessions'
        ordering = ['-started_at']

    def __str__(self):
        return f"Session {self.session_id} - {self.country_code} - {self.status}"