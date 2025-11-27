# telegram_manager/admin.py
from django.utils import timezone

from django.contrib import admin
from django.conf import settings
from .models import TelegramChannel, TelegramMessage, MessageEditHistory, MessageSendingLog
from .services import TelegramBotService


# telegram_manager/admin.py
@admin.register(TelegramChannel)
class TelegramChannelAdmin(admin.ModelAdmin):
    list_display = ['name', 'username', 'channel_id', 'country', 'is_active', 'created_at', 'bot_token_status']
    list_filter = ['country', 'is_active', 'created_at']
    search_fields = ['name', 'username', 'description']
    readonly_fields = ['created_at', 'updated_at', 'bot_token_status']
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'country', 'description')
        }),
        ('Channel Identifiers', {
            'fields': ('username', 'channel_id'),
            'description': 'Provide at least one identifier (username or channel ID)'
        }),
        ('Channel Settings', {
            'fields': ('logo', 'is_active')
        }),
        ('Bot Information', {
            'fields': ('bot_token_status',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def bot_token_status(self, obj):
        """Display bot token status"""
        token = getattr(settings, 'TELEGRAM_BOT_TOKEN', None)
        if token and token != 'your_bot_token':
            bot_service = TelegramBotService()
            bot_info = bot_service.get_bot_info()
            if bot_info:
                return f"✅ Connected as @{bot_info.get('username', 'Unknown')}"
            else:
                return "❌ Invalid token or connection failed"
        else:
            return "❌ Token not configured"

    bot_token_status.short_description = "Bot Status"


class MessageEditHistoryInline(admin.TabularInline):
    model = MessageEditHistory
    extra = 0
    readonly_fields = ['edited_by', 'edited_at', 'telegram_edit_success']
    can_delete = False


class MessageSendingLogInline(admin.TabularInline):
    model = MessageSendingLog
    extra = 0
    readonly_fields = ['attempt_time', 'success', 'error_message']
    can_delete = False


# telegram_manager/admin.py
@admin.register(TelegramMessage)
class TelegramMessageAdmin(admin.ModelAdmin):
    list_display = ['telegram_message_id', 'channel', 'status', 'reply_to_message_id_display', 'created_by', 'created_at']
    list_filter = ['status', 'channel__country', 'created_at']
    search_fields = ['message_text', 'channel__name']
    readonly_fields = ['created_at', 'updated_at', 'sent_at']
    inlines = [MessageEditHistoryInline, MessageSendingLogInline]
    actions = ['send_selected_messages', 'edit_in_telegram', 'delete_from_telegram']

    # فیلدهای قابل ویرایش
    fieldsets = (
        ('Basic Information', {
            'fields': ('channel', 'message_text', 'images')
        }),
        ('Reply Settings', {
            'fields': ('reply_to_message_id',),
            'description': 'Optional: Reply to an existing Telegram message'
        }),
        ('Status & Timing', {
            'fields': ('status', 'scheduled_time', 'sent_at')
        }),
        ('Telegram Info', {
            'fields': ('telegram_message_id',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def reply_to_message_id_display(self, obj):
        """Display reply info in list view"""
        if obj.reply_to_message_id:
            return f"↩️ {obj.reply_to_message_id}"
        return "—"

    reply_to_message_id_display.short_description = "Reply To"

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

        # اگر پیام ویرایش شده و قبلاً ارسال شده، در تلگرام هم آپدیت کن
        if change and obj.status == 'sent' and obj.telegram_message_id:
            old_message = TelegramMessage.objects.get(pk=obj.pk)
            if (old_message.message_text != obj.message_text or
                    old_message.images != obj.images):
                self._create_edit_history(old_message, obj, request.user)
                self._edit_in_telegram(obj)

    def _create_edit_history(self, old_message, new_message, user):
        """Create edit history record"""
        MessageEditHistory.objects.create(
            message=new_message,
            old_message_text=old_message.message_text,
            new_message_text=new_message.message_text,
            old_images=old_message.images,
            new_images=new_message.images,
            edited_by=user
        )

    def _edit_in_telegram(self, message):
        """Edit message in Telegram"""
        from .services import TelegramBotService

        bot_service = TelegramBotService()
        success, error = bot_service.edit_message(
            message.channel.channel_id,
            message.telegram_message_id,
            message.message_text,
            message.images
        )

        # آپدیت تاریخچه ویرایش
        if success:
            MessageEditHistory.objects.filter(message=message).latest('edited_at').update(
                telegram_edit_success=True
            )

    def send_selected_messages(self, request, queryset):
        from .services import TelegramBotService

        for message in queryset:
            if message.status in ['draft', 'failed', 'edited']:
                channel_identifier = message.channel.channel_id or message.channel.username
                reply_to_id = message.reply_to_message_id

                bot_service = TelegramBotService()
                success, telegram_id, error = bot_service.send_message(
                    channel_identifier,
                    message.message_text,
                    message.images,
                    reply_to_id
                )

                error_message_value = ""
                if error is not None:
                    error_message_value = str(error)

                MessageSendingLog.objects.create(
                    message=message,
                    success=success,
                    telegram_message_id=telegram_id,
                    error_message=error_message_value,
                    response_data={}
                )

                if success:
                    message.status = 'sent'
                    message.telegram_message_id = telegram_id
                    message.sent_at = timezone.now()
                    message.save()
                    self.message_user(request, f"Message {message.id} sent successfully")
                else:
                    message.status = 'failed'
                    message.save()
                    self.message_user(request, f"Failed to send message {message.id}: {error}", level='error')

    send_selected_messages.short_description = "Send selected messages"

    def edit_in_telegram(self, request, queryset):
        """Edit already sent messages in Telegram"""
        from .services import TelegramBotService

        for message in queryset:
            if message.status == 'sent' and message.telegram_message_id:
                bot_service = TelegramBotService()
                success, error = bot_service.edit_message(
                    message.channel.channel_id,
                    message.telegram_message_id,
                    message.message_text,
                    message.images
                )

                if success:
                    self.message_user(request, f"Message {message.id} edited successfully in Telegram")
                else:
                    self.message_user(request, f"Failed to edit message {message.id}: {error}", level='error')

    edit_in_telegram.short_description = "Edit in Telegram"

    def delete_from_telegram(self, request, queryset):
        """Delete messages from Telegram"""
        from .services import TelegramBotService

        for message in queryset:
            if message.status == 'sent' and message.telegram_message_id:
                bot_service = TelegramBotService()
                success, error = bot_service.delete_message(
                    message.channel.channel_id,
                    message.telegram_message_id
                )

                if success:
                    message.status = 'draft'
                    message.telegram_message_id = None
                    message.save()
                    self.message_user(request, f"Message {message.id} deleted from Telegram")
                else:
                    self.message_user(request, f"Failed to delete message {message.id}: {error}", level='error')

    delete_from_telegram.short_description = "Delete from Telegram"


@admin.register(MessageEditHistory)
class MessageEditHistoryAdmin(admin.ModelAdmin):
    list_display = ['message', 'edited_by', 'edited_at', 'telegram_edit_success']
    list_filter = ['edited_at', 'telegram_edit_success']
    readonly_fields = ['message', 'edited_by', 'edited_at']

    def has_add_permission(self, request):
        return False


@admin.register(MessageSendingLog)
class MessageSendingLogAdmin(admin.ModelAdmin):
    list_display = ['message', 'attempt_time', 'success', 'telegram_message_id']
    list_filter = ['success', 'attempt_time']
    readonly_fields = ['message', 'attempt_time', 'success']

    def has_add_permission(self, request):
        return False