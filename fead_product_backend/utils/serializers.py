from rest_framework import serializers
from django.contrib.auth.models import User
from django.utils import timezone
import uuid


class UserSerializer(serializers.ModelSerializer):
    """سریالایزر برای کاربران"""
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'full_name', 'is_staff', 'is_active']
        read_only_fields = ['is_staff', 'is_active']

    def get_full_name(self, obj):
        return f"{obj.first_name or ''} {obj.last_name or ''}".strip() or obj.username


class UUIDSerializer(serializers.Serializer):
    """سریالایزر برای فیلدهای UUID"""
    id = serializers.UUIDField(read_only=True)


class DateTimeSerializer(serializers.Serializer):
    """سریالایزر برای فیلدهای تاریخ و زمان"""
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)