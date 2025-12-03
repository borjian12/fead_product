from rest_framework import serializers
from .models import TelegramChannel, TelegramMessage, MessageEditHistory, MessageSendingLog
from django.contrib.auth.models import User
from rest_framework_simplejwt.tokens import RefreshToken

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email', 'is_staff']

class TelegramChannelSerializer(serializers.ModelSerializer):
    country_display = serializers.CharField(source='get_country_display', read_only=True)
    is_active_display = serializers.SerializerMethodField()

    class Meta:
        model = TelegramChannel
        fields = [
            'id', 'name', 'username', 'channel_id', 'country',
            'country_display', 'description', 'logo', 'is_active',
            'is_active_display', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

    def get_is_active_display(self, obj):
        return "فعال" if obj.is_active else "غیرفعال"

    def validate(self, data):
        if not data.get('username') and not data.get('channel_id'):
            raise serializers.ValidationError(
                "حداقل یکی از فیلدهای username یا channel_id باید پر شود."
            )
        return data


class TelegramMessageSerializer(serializers.ModelSerializer):
    channel = TelegramChannelSerializer(read_only=True)
    channel_id = serializers.PrimaryKeyRelatedField(
        queryset=TelegramChannel.objects.filter(is_active=True),
        source='channel',
        write_only=True,
        required=True
    )
    created_by = UserSerializer(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    images = serializers.JSONField(default=list)

    scheduled_time_formatted = serializers.DateTimeField(
        source='scheduled_time',
        format='%Y-%m-%d %H:%M',
        read_only=True
    )
    sent_at_formatted = serializers.DateTimeField(
        source='sent_at',
        format='%Y-%m-%d %H:%M:%S',
        read_only=True
    )

    class Meta:
        model = TelegramMessage
        fields = [
            'id', 'channel', 'channel_id', 'message_text', 'images',
            'telegram_message_id', 'reply_to_message_id', 'status',
            'status_display', 'scheduled_time', 'scheduled_time_formatted',
            'sent_at', 'sent_at_formatted', 'created_by', 'created_at',
            'updated_at'
        ]
        read_only_fields = [
            'telegram_message_id', 'status', 'sent_at', 'created_by',
            'created_at', 'updated_at'
        ]

    def create(self, validated_data):
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['created_by'] = request.user

        if 'status' not in validated_data:
            validated_data['status'] = 'draft'

        return super().create(validated_data)


class MessageEditHistorySerializer(serializers.ModelSerializer):
    edited_by = UserSerializer(read_only=True)
    edited_at_formatted = serializers.DateTimeField(
        source='edited_at',
        format='%Y-%m-%d %H:%M:%S',
        read_only=True
    )

    class Meta:
        model = MessageEditHistory
        fields = [
            'id', 'message', 'old_message_text', 'new_message_text',
            'old_images', 'new_images', 'edited_by', 'edited_at',
            'edited_at_formatted', 'telegram_edit_success'
        ]
        read_only_fields = ['edited_at', 'edited_by']


class MessageSendingLogSerializer(serializers.ModelSerializer):
    attempt_time_formatted = serializers.DateTimeField(
        source='attempt_time',
        format='%Y-%m-%d %H:%M:%S',
        read_only=True
    )

    class Meta:
        model = MessageSendingLog
        fields = [
            'id', 'message', 'attempt_time', 'attempt_time_formatted',
            'success', 'telegram_message_id', 'error_message',
            'response_data'
        ]
        read_only_fields = ['attempt_time']


class SendMessageSerializer(serializers.Serializer):
    channel_id = serializers.UUIDField(required=True)
    message_text = serializers.CharField(required=True)
    images = serializers.ListField(
        child=serializers.URLField(),
        required=False,
        default=[]
    )
    reply_to_message_id = serializers.IntegerField(
        required=False,
        allow_null=True
    )
    schedule_time = serializers.DateTimeField(
        required=False,
        allow_null=True
    )


class EditMessageSerializer(serializers.Serializer):
    new_message_text = serializers.CharField(required=True)
    images = serializers.ListField(
        child=serializers.URLField(),
        required=False,
        default=[]
    )


class ReplyMessageSerializer(serializers.Serializer):
    reply_to_message_id = serializers.IntegerField(required=True)
    message_text = serializers.CharField(required=True)
    images = serializers.ListField(
        child=serializers.URLField(),
        required=False,
        default=[]
    )


class BulkSendSerializer(serializers.Serializer):
    channel_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=True
    )
    message_text = serializers.CharField(required=True)
    images = serializers.ListField(
        child=serializers.URLField(),
        required=False,
        default=[]
    )