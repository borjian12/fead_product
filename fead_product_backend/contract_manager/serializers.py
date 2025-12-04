from rest_framework import serializers

from auth_app.models import SellerProfile
from .models import Product, Country, ProductChannel
from amazon_app.models import AmazonProduct


class CountrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Country
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']


class AmazonProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = AmazonProduct
        fields = [
            'asin', 'title','rating',
            'review_count', 'brand', 'image_url',
            'description', 'last_crawled'
        ]


class ProductSerializer(serializers.ModelSerializer):
    country = CountrySerializer(read_only=True)
    country_code = serializers.CharField(write_only=True)
    amazon_data = AmazonProductSerializer(source='amazon_product', read_only=True)
    owner_id = serializers.PrimaryKeyRelatedField(
        source='owner',
        queryset=SellerProfile.objects.all(),
        write_only=True,
        required=False
    )

    class Meta:
        model = Product
        fields = [
            'id', 'asin', 'title', 'country', 'country_code',
            'description', 'search_guide', 'product_url',
            'daily_max_quantity', 'total_max_quantity', 'current_quantity',
            'is_active', 'is_stopped', 'variant_asins',
            'amazon_data', 'owner_id', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'product_url', 'created_at', 'updated_at', 'current_quantity']

    def create(self, validated_data):
        country_code = validated_data.pop('country_code', 'US')
        owner = validated_data.pop('owner', None)

        # کشور را پیدا کن
        try:
            country = Country.objects.get(code=country_code)
        except Country.DoesNotExist:
            raise serializers.ValidationError(f'Country {country_code} not found')

        # اگر owner مشخص نشده، از کاربر فعلی استفاده کن
        if not owner and hasattr(self.context['request'].user, 'seller_profile'):
            owner = self.context['request'].user.seller_profile

        if not owner:
            raise serializers.ValidationError('Owner is required')

        # ایجاد محصول
        product = Product.objects.create(
            country=country,
            owner=owner,
            **validated_data
        )

        return product

    def update(self, instance, validated_data):
        # حذف country_code از validated_data اگر وجود دارد
        validated_data.pop('country_code', None)
        validated_data.pop('owner', None)  # مالک را تغییر ندهیم

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        return instance


class ProductChannelSerializer(serializers.ModelSerializer):
    channel_name = serializers.CharField(source='channel.name', read_only=True)
    channel_id = serializers.CharField(source='channel.channel_id', read_only=True)

    class Meta:
        model = ProductChannel
        fields = [
            'id', 'channel_name', 'channel_id', 'telegram_message_id',
            'status', 'sent_at', 'view_count', 'click_count',
            'auto_update', 'notify_on_change'
        ]
        read_only_fields = fields


class ProductDetailSerializer(serializers.ModelSerializer):
    country = CountrySerializer(read_only=True)
    amazon_data = AmazonProductSerializer(source='amazon_product', read_only=True)
    telegram_messages = ProductChannelSerializer(source='productchannel_set', many=True, read_only=True)

    class Meta:
        model = Product
        fields = [
            'id', 'asin', 'title', 'country', 'description', 'search_guide',
            'product_url', 'daily_max_quantity', 'total_max_quantity', 'current_quantity',
            'is_active', 'is_stopped', 'variant_asins',
            'amazon_data', 'telegram_messages',
            'created_at', 'updated_at'
        ]