# telegram_manager/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .models import TelegramMessage, TelegramChannel, MessageEditHistory
from .services import TelegramBotService


@login_required
def message_list(request):
    messages = TelegramMessage.objects.filter(created_by=request.user).select_related('channel')
    return render(request, 'telegram_manager/message_list.html', {
        'messages': messages
    })


@login_required
def create_message(request, channel_id=None):
    channels = TelegramChannel.objects.filter(is_active=True)

    if request.method == 'POST':
        channel_id = request.POST.get('channel')
        message_text = request.POST.get('message_text')
        images = request.POST.get('images', '').split(',')

        channel = get_object_or_404(TelegramChannel, id=channel_id)

        message = TelegramMessage.objects.create(
            channel=channel,
            message_text=message_text,
            images=[img.strip() for img in images if img.strip()],
            created_by=request.user
        )

        messages.success(request, 'Message created successfully!')
        return redirect('telegram_manager:message_list')

    return render(request, 'telegram_manager/create_message.html', {
        'channels': channels,
        'selected_channel_id': channel_id
    })


@login_required
def edit_message(request, message_id):
    message = get_object_or_404(TelegramMessage, id=message_id, created_by=request.user)

    if request.method == 'POST':
        old_text = message.message_text
        old_images = message.images

        message.message_text = request.POST.get('message_text')
        message.images = [img.strip() for img in request.POST.get('images', '').split(',') if img.strip()]
        message.status = 'edited'
        message.save()

        # Create edit history
        MessageEditHistory.objects.create(
            message=message,
            old_message_text=old_text,
            new_message_text=message.message_text,
            old_images=old_images,
            new_images=message.images,
            edited_by=request.user
        )

        # If message was already sent to Telegram, update there too
        if message.telegram_message_id:
            bot_service = TelegramBotService()
            success, error = bot_service.edit_message(
                message.channel.channel_id,
                message.telegram_message_id,
                message.message_text
            )

            # Update edit history with Telegram result
            if success:
                MessageEditHistory.objects.filter(message=message).latest('edited_at').update(
                    telegram_edit_success=True
                )

        messages.success(request, 'Message updated successfully!')
        return redirect('telegram_manager:message_list')

    return render(request, 'telegram_manager/edit_message.html', {
        'message': message
    })


@login_required
def send_message(request, message_id):
    message = get_object_or_404(TelegramMessage, id=message_id, created_by=request.user)

    if message.status in ['draft', 'failed']:
        bot_service = TelegramBotService()
        success, telegram_id, error = bot_service.send_message(
            message.channel.channel_id,
            message.message_text,
            message.images
        )

        if success:
            message.status = 'sent'
            message.telegram_message_id = telegram_id
            message.sent_at = timezone.now()
            message.save()
            messages.success(request, 'Message sent successfully!')
        else:
            message.status = 'failed'
            message.save()
            messages.error(request, f'Failed to send message: {error}')

    return redirect('telegram_manager:message_list')


@login_required
def delete_message(request, message_id):
    message = get_object_or_404(TelegramMessage, id=message_id, created_by=request.user)

    # If message was sent to Telegram, delete it there too
    if message.telegram_message_id and message.status == 'sent':
        bot_service = TelegramBotService()
        bot_service.delete_message(message.channel.channel_id, message.telegram_message_id)

    message.delete()
    messages.success(request, 'Message deleted successfully!')
    return redirect('telegram_manager:message_list')