# amazon_app/serializers.py
from rest_framework import serializers
from drf_yasg.utils import swagger_serializer_method
from .models import AmazonProduct, AmazonProductPrice
from contract_manager.models import Product


class ProductPriceSerializer(serializers.ModelSerializer):
    """Serializer برای قیمت‌های محصول آمازون"""

    class Meta:
        model = AmazonProductPrice
        fields = [
            'id', 'price', 'currency', 'seller', 'availability',
            'crawl_timestamp', 'shipping_info',
            # 'discount_percentage', 'original_price', 'stock_quantity',
            # 'buybox_winner', 'created_at', 'updated_at',
            # 'is_fba', 'is_amazon',
        ]
        read_only_fields = fields


class AmazonProductSerializer(serializers.ModelSerializer):
    """Serializer پایه برای محصولات آمازون"""

    current_price = serializers.SerializerMethodField()

    class Meta:
        model = AmazonProduct
        fields = [
            'asin', 'country_code', 'product_url', 'title', 'brand', 'category',
            'rating', 'review_count', 'image_url', 'condition',
            'domain', 'features', 'description', 'specifications',
            'last_crawled', 'created_at',
            'updated_at', 'current_price'
            # 'dimensions', 'weight',
        ]
        read_only_fields = fields

    def get_current_price(self, obj):
        """دریافت آخرین قیمت محصول"""
        latest_price = obj.prices.order_by('-crawl_timestamp').first()
        if latest_price:
            serializer = ProductPriceSerializer(latest_price)
            return serializer.data
        return None


class AmazonProductListSerializer(AmazonProductSerializer):
    """Serializer برای لیست محصولات"""

    price_statistics = serializers.SerializerMethodField()
    is_used_in_system = serializers.SerializerMethodField()
    system_products_count = serializers.SerializerMethodField()

    class Meta(AmazonProductSerializer.Meta):
        fields = AmazonProductSerializer.Meta.fields + [
            'price_statistics', 'is_used_in_system', 'system_products_count'
        ]

    def get_price_statistics(self, obj):
        """آمار قیمت محصول"""
        from django.db.models import Min, Max, Avg, Count

        stats = obj.prices.aggregate(
            min_price=Min('price'),
            max_price=Max('price'),
            avg_price=Avg('price'),
            price_count=Count('price')
        )

        return {
            'min_price': float(stats['min_price']) if stats['min_price'] else None,
            'max_price': float(stats['max_price']) if stats['max_price'] else None,
            'avg_price': float(stats['avg_price']) if stats['avg_price'] else None,
            'price_count': stats['price_count'] or 0
        }

    def get_is_used_in_system(self, obj):
        """آیا محصول در سیستم ما استفاده شده است؟"""
        return Product.objects.filter(
            asin=obj.asin,
            country__code=obj.country_code
        ).exists()

    def get_system_products_count(self, obj):
        """تعداد استفاده‌های محصول در سیستم ما"""
        return Product.objects.filter(
            asin=obj.asin,
            country__code=obj.country_code
        ).count()


class AmazonProductDetailSerializer(AmazonProductSerializer):
    """Serializer برای جزئیات کامل محصول"""

    price_statistics = serializers.SerializerMethodField()
    price_history = serializers.SerializerMethodField()
    system_products = serializers.SerializerMethodField()
    available_in_other_countries = serializers.SerializerMethodField()

    class Meta(AmazonProductSerializer.Meta):
        fields = AmazonProductSerializer.Meta.fields + [
            'price_statistics', 'price_history', 'system_products',
            'available_in_other_countries'
        ]

    def get_price_statistics(self, obj):
        """آمار کامل قیمت"""
        from django.db.models import Min, Max, Avg, Count, Q
        from datetime import datetime, timedelta

        # محاسبه آمار کلی
        stats = obj.prices.aggregate(
            min_price=Min('price'),
            max_price=Max('price'),
            avg_price=Avg('price'),
            price_count=Count('price'),
            first_price_date=Min('crawl_timestamp'),
            last_price_date=Max('crawl_timestamp'),
            total_sellers=Count('seller', distinct=True),
            amazon_seller_count=Count('seller', distinct=True, filter=Q(seller='Amazon')),
            fba_count=Count('id', filter=Q(is_fba=True)),
        )

        # محاسبه تغییرات قیمت
        oldest_price = obj.prices.order_by('crawl_timestamp').first()
        latest_price = obj.prices.order_by('-crawl_timestamp').first()

        price_change = None
        if latest_price and oldest_price and latest_price != oldest_price:
            price_change = {
                'old_price': float(oldest_price.price),
                'new_price': float(latest_price.price),
                'change_amount': float(latest_price.price) - float(oldest_price.price),
                'change_percentage': ((float(latest_price.price) - float(oldest_price.price)) / float(
                    oldest_price.price)) * 100 if float(oldest_price.price) > 0 else 0,
                'time_period_days': (latest_price.crawl_timestamp - oldest_price.crawl_timestamp).days
            }

        # آمار ۳۰ روز اخیر
        thirty_days_ago = datetime.now() - timedelta(days=30)
        recent_stats = obj.prices.filter(
            crawl_timestamp__gte=thirty_days_ago
        ).aggregate(
            recent_min_price=Min('price'),
            recent_max_price=Max('price'),
            recent_avg_price=Avg('price'),
            recent_count=Count('price')
        )

        return {
            'all_time': {
                'min_price': float(stats['min_price']) if stats['min_price'] else None,
                'max_price': float(stats['max_price']) if stats['max_price'] else None,
                'avg_price': float(stats['avg_price']) if stats['avg_price'] else None,
                'price_count': stats['price_count'] or 0,
                'first_price_date': stats['first_price_date'].isoformat() if stats['first_price_date'] else None,
                'last_price_date': stats['last_price_date'].isoformat() if stats['last_price_date'] else None,
                'total_sellers': stats['total_sellers'] or 0,
                'amazon_seller_count': stats['amazon_seller_count'] or 0,
                'fba_count': stats['fba_count'] or 0,
            },
            'last_30_days': {
                'min_price': float(recent_stats['recent_min_price']) if recent_stats['recent_min_price'] else None,
                'max_price': float(recent_stats['recent_max_price']) if recent_stats['recent_max_price'] else None,
                'avg_price': float(recent_stats['recent_avg_price']) if recent_stats['recent_avg_price'] else None,
                'price_count': recent_stats['recent_count'] or 0,
            },
            'price_change_over_time': price_change
        }

    def get_price_history(self, obj):
        """تاریخچه قیمت"""
        request = self.context.get('request')
        history_days = int(request.query_params.get('history_days', 90)) if request else 90

        from datetime import datetime, timedelta
        cutoff_date = datetime.now() - timedelta(days=history_days)

        price_history = obj.prices.filter(
            crawl_timestamp__gte=cutoff_date
        ).order_by('-crawl_timestamp')[:100]  # محدود به ۱۰۰ رکورد

        return ProductPriceSerializer(price_history, many=True).data

    def get_system_products(self, obj):
        """محصولات مرتبط در سیستم ما"""
        system_products = Product.objects.filter(
            asin=obj.asin,
            country__code=obj.country_code
        ).select_related('owner')

        if not system_products.exists():
            return []

        return [
            {
                'id': str(sp.id),
                'title': sp.title,
                'owner': {
                    'id': str(sp.owner.id),
                    'company_name': sp.owner.company_name,
                    'seller_type': sp.owner.seller_type
                } if sp.owner else None,
                'daily_max_quantity': sp.daily_max_quantity,
                'total_max_quantity': sp.total_max_quantity,
                'created_at': sp.created_at.isoformat() if sp.created_at else None,
                'status': 'active' if not sp.is_stopped else 'stopped'
            }
            for sp in system_products
        ]

    def get_available_in_other_countries(self, obj):
        """سایر نسخه‌های کشور"""
        other_countries = AmazonProduct.objects.filter(
            asin=obj.asin
        ).exclude(country_code=obj.country_code)

        if not other_countries.exists():
            return []

        result = []
        for oc in other_countries:
            latest_price = oc.prices.order_by('-crawl_timestamp').first()
            result.append({
                'country_code': oc.country_code,
                'domain': oc.domain,
                'last_crawled': oc.last_crawled.isoformat() if oc.last_crawled else None,
                'current_price': float(latest_price.price) if latest_price else None,
                'currency': latest_price.currency if latest_price else None
            })

        return result


# Serializerهای درخواست (برای Swagger بهتر از swagger_serializer_method استفاده می‌کنیم)
class CrawlRequestSerializer(serializers.Serializer):
    """Serializer برای درخواست crawl محصولات"""

    asins = serializers.ListField(
        child=serializers.CharField(max_length=20),
        required=True,
        help_text="لیست ASIN محصولات"
    )
    country_code = serializers.CharField(
        max_length=2,
        default='US',
        help_text="کد کشور"
    )
    driver_name = serializers.CharField(
        max_length=50,
        default='amazon_crawler',
        help_text="نام درایور"
    )
    session_id = serializers.CharField(
        max_length=100,
        required=False,
        allow_null=True,
        allow_blank=True,
        help_text="شناسه سشن"
    )

    class Meta:
        ref_name = "AmazonCrawlRequest"


class CrawlSingleRequestSerializer(serializers.Serializer):
    """Serializer برای درخواست crawl یک محصول"""

    asin = serializers.CharField(
        max_length=20,
        required=False,
        allow_blank=True,
        help_text="ASIN محصول"
    )
    url = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="URL محصول"
    )
    country_code = serializers.CharField(
        max_length=2,
        default='US',
        help_text="کد کشور"
    )
    driver_name = serializers.CharField(
        max_length=50,
        default='amazon_crawler',
        help_text="نام درایور"
    )

    def validate(self, data):
        """اعتبارسنجی: حداقل یکی از asin یا url باید وجود داشته باشد"""
        if not data.get('asin') and not data.get('url'):
            raise serializers.ValidationError(
                "Either ASIN or URL is required"
            )
        return data


class VerifyMatchRequestSerializer(serializers.Serializer):
    """Serializer برای تأیید تطابق محصول"""

    url = serializers.URLField(
        required=True,
        help_text="URL محصول"
    )
    asin = serializers.CharField(
        max_length=20,
        required=True,
        help_text="ASIN مورد انتظار"
    )


class CrawlByURLRequestSerializer(serializers.Serializer):
    """Serializer برای crawl با URL"""

    url = serializers.URLField(
        required=True,
        help_text="URL محصول"
    )


class PriceHistoryRequestSerializer(serializers.Serializer):
    """Serializer برای درخواست تاریخچه قیمت"""

    country_code = serializers.CharField(
        max_length=2,
        required=False,
        allow_blank=True,
        help_text="کد کشور"
    )
    days = serializers.IntegerField(
        min_value=1,
        max_value=365,
        default=30,
        help_text="تعداد روزهای تاریخچه"
    )
    granularity = serializers.ChoiceField(
        choices=['daily', 'hourly', 'all'],
        default='daily',
        help_text="دقت داده‌ها"
    )


class ProductStatsSerializer(serializers.Serializer):
    """Serializer برای آمار محصول"""

    days = serializers.IntegerField(
        min_value=1,
        max_value=365,
        default=7,
        help_text="تعداد روزهای آمار"
    )
