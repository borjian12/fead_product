# telegram_manager/services.py
import requests
import logging
from django.utils import timezone
from django.conf import settings
from .models import TelegramMessage, MessageSendingLog, MessageEditHistory

logger = logging.getLogger(__name__)


class TelegramBotService:
    def __init__(self, bot_token=None):
        self.bot_token = bot_token or getattr(settings, 'TELEGRAM_BOT_TOKEN', None)
        if not self.bot_token:
            raise ValueError("Telegram bot token is not configured in settings")
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"

    def send_message(self, channel_id, message_text, images=None, reply_to_message_id=None):
        """
        Send message to Telegram channel
        Returns: (success, telegram_message_id, error_message)
        """
        try:
            # If there are images, send as media group
            if images and len(images) > 0:
                return self._send_media_group(channel_id, message_text, images, reply_to_message_id)
            else:
                # Send text message only
                return self._send_text_message(channel_id, message_text, reply_to_message_id)

        except Exception as e:
            logger.error(f"Error sending message to channel {channel_id}: {e}")
            return False, None, str(e)

    def _send_text_message(self, channel_id, message_text, reply_to_message_id=None):
        """Send simple text message"""
        url = f"{self.base_url}/sendMessage"
        payload = {
            'chat_id': channel_id,
            'text': message_text,
            'parse_mode': 'HTML'
        }

        # Add reply if specified
        if reply_to_message_id:
            payload['reply_to_message_id'] = reply_to_message_id

        response = requests.post(url, json=payload)
        data = response.json()

        if data.get('ok'):
            message_id = data['result']['message_id']
            return True, message_id, ""
        else:
            error_msg = data.get('description', 'Unknown error')
            return False, None, str(error_msg)

    def _send_media_group(self, channel_id, message_text, images, reply_to_message_id=None):
        """Send message with media group"""
        url = f"{self.base_url}/sendMediaGroup"

        # Prepare media array
        media = []
        for i, image_url in enumerate(images):
            media_item = {
                'type': 'photo',
                'media': image_url
            }
            # Add caption only to the first image
            if i == 0:
                media_item['caption'] = message_text
                media_item['parse_mode'] = 'HTML'
            media.append(media_item)

        payload = {
            'chat_id': channel_id,
            'media': media
        }

        # Add reply if specified (note: media groups may not support reply in all cases)
        if reply_to_message_id:
            payload['reply_to_message_id'] = reply_to_message_id

        response = requests.post(url, json=payload)
        data = response.json()

        if data.get('ok'):
            # Get message ID from the first media item
            message_id = data['result'][0]['message_id']
            return True, message_id, ""
        else:
            error_msg = data.get('description', 'Unknown error')
            return False, None, str(error_msg)

    def edit_message(self, channel_id, message_id, new_text, images=None):
        """
        Edit existing message in Telegram
        Note: Telegram doesn't allow editing media, only text and caption
        """
        try:
            # If it's a media message, edit caption
            if images and len(images) > 0:
                return self._edit_message_caption(channel_id, message_id, new_text)
            else:
                # Edit text message
                return self._edit_message_text(channel_id, message_id, new_text)

        except Exception as e:
            logger.error(f"Error editing message {message_id}: {e}")
            return False, str(e)

    def _edit_message_text(self, channel_id, message_id, new_text):
        """Edit text message"""
        url = f"{self.base_url}/editMessageText"
        payload = {
            'chat_id': channel_id,
            'message_id': message_id,
            'text': new_text,
            'parse_mode': 'HTML'
        }

        response = requests.post(url, json=payload)
        data = response.json()

        if data.get('ok'):
            return True, ""
        else:
            error_msg = data.get('description', 'Unknown error')
            return False, error_msg

    def _edit_message_caption(self, channel_id, message_id, new_caption):
        """Edit media message caption"""
        url = f"{self.base_url}/editMessageCaption"
        payload = {
            'chat_id': channel_id,
            'message_id': message_id,
            'caption': new_caption,
            'parse_mode': 'HTML'
        }

        response = requests.post(url, json=payload)
        data = response.json()

        if data.get('ok'):
            return True, ""
        else:
            error_msg = data.get('description', 'Unknown error')
            return False, error_msg

    def delete_message(self, channel_id, message_id):
        """Delete message from Telegram"""
        try:
            url = f"{self.base_url}/deleteMessage"
            payload = {
                'chat_id': channel_id,
                'message_id': message_id
            }

            response = requests.post(url, json=payload)
            data = response.json()

            return data.get('ok', False), data.get('description', '')

        except Exception as e:
            logger.error(f"Error deleting message {message_id}: {e}")
            return False, str(e)

    def send_reply(self, channel_id, reply_to_message_id, message_text, images=None):
        """
        Send reply to existing message
        """
        return self.send_message(channel_id, message_text, images, reply_to_message_id)

    def get_bot_info(self):
        """Get bot information from Telegram API"""
        try:
            url = f"{self.base_url}/getMe"
            response = requests.get(url)
            data = response.json()

            if data.get('ok'):
                return data['result']
            else:
                return None
        except Exception as e:
            logger.error(f"Error getting bot info: {e}")
            return None


def get_bot_service():
    """Helper function to get TelegramBotService instance"""
    return TelegramBotService()