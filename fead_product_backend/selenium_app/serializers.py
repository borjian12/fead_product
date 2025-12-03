# selenium_app/serializers.py
from rest_framework import serializers
from .models import SeleniumDriver, CrawlRequest, DriverSession


class SeleniumDriverSerializer(serializers.ModelSerializer):
    class Meta:
        model = SeleniumDriver
        fields = '__all__'
        read_only_fields = ('created_at', 'last_used')


class CrawlRequestSerializer(serializers.ModelSerializer):
    driver_name = serializers.CharField(source='driver.name', read_only=True, allow_null=True)
    driver_type = serializers.CharField(source='driver.driver_type', read_only=True, allow_null=True)

    class Meta:
        model = CrawlRequest
        fields = '__all__'
        read_only_fields = ('created_at', 'started_at', 'completed_at', 'html_content', 'error_message')


class CrawlRequestCreateSerializer(serializers.Serializer):
    driver_name = serializers.CharField(max_length=100, required=False, default='default')
    url = serializers.URLField(max_length=500)
    requester = serializers.CharField(max_length=100, required=False, default='unknown')
    metadata = serializers.JSONField(required=False, default=dict)


class DriverSessionSerializer(serializers.ModelSerializer):
    driver_name = serializers.CharField(source='driver.name', read_only=True)

    class Meta:
        model = DriverSession
        fields = '__all__'
        read_only_fields = ('created_at', 'last_activity')
