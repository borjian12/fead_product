# telegram_manager/models.py
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
import uuid
import json

from django.conf import settings


class TelegramChannel(models.Model):
    COUNTRY_CHOICES = [
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
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, verbose_name="Channel Name")
    username = models.CharField(
        max_length=255,
        verbose_name="Channel Username",
        help_text="@channel_username",
        blank=True,  # Make it optional
        null=True,  # Allow NULL in database
        unique=True  # Ensure uniqueness when provided
    )
    channel_id = models.BigIntegerField(
        verbose_name="Channel ID",
        blank=True,  # Make it optional
        null=True,  # Allow NULL in database
        unique=True  # Ensure uniqueness when provided
    )
    country = models.CharField(max_length=2, choices=COUNTRY_CHOICES, verbose_name="Country")
    description = models.TextField(blank=True, verbose_name="Description")
    logo = models.ImageField(upload_to='channel_logos/', blank=True, null=True, verbose_name="Logo")
    is_active = models.BooleanField(default=True, verbose_name="Active")
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def bot_token(self):
        """Get bot token from Django settings"""
        return getattr(settings, 'TELEGRAM_BOT_TOKEN', None)

    class Meta:
        verbose_name = "Telegram Channel"
        verbose_name_plural = "Telegram Channels"
        ordering = ['country', 'name']
        db_table = 'telegram_channels'
        constraints = [
            models.CheckConstraint(
                check=(
                        models.Q(username__isnull=False) |
                        models.Q(channel_id__isnull=False)
                ),
                name='at_least_one_identifier'
            )
        ]

    def __str__(self):
        return f"{self.name} ({self.country})"

    def clean(self):
        """Validation to ensure at least one identifier is provided"""
        from django.core.exceptions import ValidationError

        if not self.username and not self.channel_id:
            raise ValidationError(
                "Either username or channel_id must be provided."
            )

    def save(self, *args, **kwargs):
        """Override save to run validation"""
        self.clean()
        super().save(*args, **kwargs)

    def get_channel_identifier(self):
        """Get the available channel identifier (username or channel_id)"""
        return self.username or str(self.channel_id)


# telegram_manager/models.py
class TelegramMessage(models.Model):
    MESSAGE_STATUS = [
        ('draft', 'Draft'),
        ('scheduled', 'Scheduled'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
        ('edited', 'Edited'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    channel = models.ForeignKey(TelegramChannel, on_delete=models.CASCADE, verbose_name="Channel")
    message_text = models.TextField(verbose_name="Message Text")
    images = models.JSONField(default=list, blank=True, verbose_name="Images List",
                              help_text="List of image URLs as JSON")
    telegram_message_id = models.BigIntegerField(null=True, blank=True, verbose_name="Telegram Message ID")

    # 🔥 فیلد جدید برای ریپلای
    reply_to_message_id = models.BigIntegerField(
        null=True,
        blank=True,
        verbose_name="Reply to Message ID",
        help_text="Telegram message ID to reply to (optional)"
    )
    status = models.CharField(max_length=20, choices=MESSAGE_STATUS, default='draft', verbose_name="Status")
    scheduled_time = models.DateTimeField(null=True, blank=True, verbose_name="Scheduled Time")
    sent_at = models.DateTimeField(null=True, blank=True, verbose_name="Sent At")
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Created By")
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Telegram Message"
        verbose_name_plural = "Telegram Messages"
        ordering = ['-created_at']
        db_table = 'telegram_messages'

    def __str__(self):
        return f"Message {self.telegram_message_id or 'Draft'} - {self.channel.name}"


class MessageEditHistory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    message = models.ForeignKey(TelegramMessage, on_delete=models.CASCADE, related_name='edit_history')
    old_message_text = models.TextField(verbose_name="Old Message Text")
    new_message_text = models.TextField(verbose_name="New Message Text")
    old_images = models.JSONField(default=list, verbose_name="Old Images")
    new_images = models.JSONField(default=list, verbose_name="New Images")
    edited_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Edited By")
    edited_at = models.DateTimeField(default=timezone.now)
    telegram_edit_success = models.BooleanField(default=False, verbose_name="Telegram Edit Success")

    class Meta:
        verbose_name = "Message Edit History"
        verbose_name_plural = "Message Edit History"
        ordering = ['-edited_at']
        db_table = 'telegram_message_histories'

    def __str__(self):
        return f"Edit history for message {self.message.id}"


class MessageSendingLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    message = models.ForeignKey(TelegramMessage, on_delete=models.CASCADE, related_name='sending_logs')
    attempt_time = models.DateTimeField(default=timezone.now)
    success = models.BooleanField(default=False)
    telegram_message_id = models.BigIntegerField(null=True, blank=True)
    error_message = models.TextField(blank=True, default="")
    response_data = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = "Message Sending Log"
        verbose_name_plural = "Message Sending Logs"
        ordering = ['-attempt_time']
        db_table = 'telegram_message_sending_logs'