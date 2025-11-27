# auth_app/serializers.py
from rest_framework import serializers
from rest_framework import serializers
from django.contrib.auth.models import User
from .models import TelegramProfile

class TelegramAuthSerializer(serializers.Serializer):
    init_data = serializers.CharField(required=True, max_length=2000)

    def validate_init_data(self, value):
        if not value:
            raise serializers.ValidationError("init_data cannot be empty")
        return value


class UserProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['first_name', 'last_name']
        extra_kwargs = {
            'first_name': {'required': False},
            'last_name': {'required': False},
        }


class TelegramProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = TelegramProfile
        fields = [
            'email',
            'people',
            'amazon_profile_link',
            'amazon_reviews_count',
            'amazon_purchases_count'
        ]
        extra_kwargs = {
            'email': {'required': False},
            'people': {'required': False},
            'amazon_profile_link': {'required': False},
            'amazon_reviews_count': {'required': False},
            'amazon_purchases_count': {'required': False},
        }


class UserProfileSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    username = serializers.CharField(read_only=True)
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    telegram_id = serializers.IntegerField(read_only=True)
    language_code = serializers.CharField(read_only=True)
    is_premium = serializers.BooleanField(read_only=True)
    photo_url = serializers.URLField(read_only=True)

    # فیلدهای جدید
    email = serializers.EmailField(read_only=True)
    people = serializers.CharField(read_only=True)
    amazon_profile_link = serializers.URLField(read_only=True)
    amazon_reviews_count = serializers.IntegerField(read_only=True)
    amazon_purchases_count = serializers.IntegerField(read_only=True)