# contract_manager/serializers.py
from rest_framework import serializers
from .models import Product, Country, ProductChannel, Seller, AdminProfile, Agent
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

    class Meta:
        model = Product
        fields = [
            'id', 'asin', 'title', 'country', 'country_code',
            'description', 'search_guide', 'product_url',
            'daily_max_quantity', 'total_max_quantity', 'current_quantity',
            'is_active', 'is_stopped', 'variant_asins',
            'amazon_data', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'product_url', 'created_at', 'updated_at', 'current_quantity']

    def create(self, validated_data):
        country_code = validated_data.pop('country_code', 'US')
        seller = validated_data.pop('owner')

        # کشور را پیدا کن
        try:
            country = Country.objects.get(code=country_code)
        except Country.DoesNotExist:
            raise serializers.ValidationError(f'Country {country_code} not found')

        # ایجاد محصول
        product = Product.objects.create(
            country=country,
            owner=seller,
            **validated_data
        )

        return product

    def update(self, instance, validated_data):
        # حذف country_code از validated_data اگر وجود دارد
        validated_data.pop('country_code', None)

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


class SellerSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = Seller
        fields = '__all__'
        read_only_fields = ['created_at']


class AgentSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)
    assigned_sellers_count = serializers.SerializerMethodField()

    class Meta:
        model = Agent
        fields = '__all__'
        read_only_fields = ['created_at']

    def get_assigned_sellers_count(self, obj):
        return obj.assigned_sellers.count()


class AdminProfileSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = AdminProfile
        fields = '__all__'
        read_only_fields = ['created_at']