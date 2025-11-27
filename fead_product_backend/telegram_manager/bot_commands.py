# telegram_manager/bot_commands.py
import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class TelegramBotCommands:
    def __init__(self, bot_token=None):
        self.bot_token = bot_token or getattr(settings, 'TELEGRAM_BOT_TOKEN', None)
        if not self.bot_token:
            raise ValueError("Telegram bot token is not configured in settings")
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"

    def process_update(self, update):
        """Process updates received from Telegram"""
        try:
            if 'message' in update:
                return self._process_message(update['message'])
            elif 'channel_post' in update:
                return self._process_channel_post(update['channel_post'])
            elif 'callback_query' in update:
                return self._process_callback_query(update['callback_query'])
            else:
                print(f"🔔 Unknown update type: {update.keys()}")

        except Exception as e:
            logger.error(f"Error processing update: {e}")
            print(f"❌ Error processing update: {e}")

    def _process_message(self, message):
        """Process user messages"""
        chat_id = message['chat']['id']
        text = message.get('text', '').strip()

        print(f"📨 Received message: {text} from chat: {chat_id}")

        if text == '/start':
            return self._send_welcome_message(chat_id)
        elif text == '/get_id':
            return self._send_chat_id(chat_id, message['chat'])
        elif text == '/help':
            return self._send_help_message(chat_id)
        elif text.startswith('/'):
            return self._send_unknown_command(chat_id)
        else:
            # For regular messages, send simple response
            return self._send_simple_response(chat_id)

    def _process_channel_post(self, channel_post):
        """Process channel posts"""
        chat_id = channel_post['chat']['id']
        text = channel_post.get('text', '').strip()

        print(f"📢 Channel post: {text} in channel: {chat_id}")

        if text == '/get_id':
            return self._send_channel_id(chat_id, channel_post['chat'])
        elif text.startswith('/'):
            print(f"⚠️ Unknown command in channel: {text}")

    def _process_callback_query(self, callback_query):
        """Process callback queries from inline keyboard"""
        # This is used for inline keyboard buttons
        # Simple implementation for now
        chat_id = callback_query['message']['chat']['id']
        data = callback_query.get('data', '')

        print(f"🔘 Callback query: {data} from chat: {chat_id}")

        # Answer callback query (required)
        self._answer_callback_query(callback_query['id'])

        # Process data
        if data == 'get_chat_id':
            return self._send_chat_id(chat_id, callback_query['message']['chat'])

    def _send_welcome_message(self, chat_id):
        """Send welcome message"""
        message = """
🤖 **Welcome to Channel Management Bot!**

📋 **Available Commands:**
/get_id - Get chat or channel ID
/help - Help guide

💡 To get channel ID, add bot to channel and send /get_id command.
        """
        return self._send_message(chat_id, message)

    def _send_help_message(self, chat_id):
        """Send help message"""
        message = """
📖 **Bot Guide:**

🆔 **Get ID:**
• In private chat: /get_id
• In channel: Add bot and send /get_id

🔧 **How to use:**
1. Use the received ID in channel management system
2. You can send messages through the system
3. Bot must be admin in the channel

📞 **Support:** Contact admin if you have issues.
        """
        return self._send_message(chat_id, message)

    def _send_chat_id(self, chat_id, chat_info):
        """Send chat ID to user"""
        chat_type = chat_info.get('type', 'unknown')
        chat_title = chat_info.get('title', chat_info.get('first_name', 'Unknown'))
        chat_username = chat_info.get('username', 'Not available')

        message = f"""
💬 **Chat Information:**

📝 **Type:** {self._get_chat_type_english(chat_type)}
🏷️ **Title:** {chat_title}
👤 **Username:** @{chat_username}
🆔 **Numeric ID:** `{chat_id}`

💡 Use this numeric ID in the management system.
        """
        return self._send_message(chat_id, message)

    def _send_channel_id(self, chat_id, chat_info):
        """Send channel ID"""
        message = f"""
📢 **Channel Information:**

🏷️ **Name:** {chat_info.get('title', 'Unknown')}
👤 **Username:** @{chat_info.get('username', 'Private')}
🆔 **Numeric ID:** `{chat_id}`

💡 Use this numeric ID in the channel management system.
        """
        return self._send_message(chat_id, message)

    def _send_unknown_command(self, chat_id):
        """Send message for unknown command"""
        message = """
❌ **Unknown Command**

📋 **Available Commands:**
/get_id - Get chat or channel ID
/start - Start using the bot
/help - Help guide
        """
        return self._send_message(chat_id, message)

    def _send_simple_response(self, chat_id):
        """Send simple response for regular messages"""
        message = "🤖 I'm a channel management bot. Use /help to see available commands."
        return self._send_message(chat_id, message)

    def _get_chat_type_english(self, chat_type):
        """Convert chat type to English"""
        types = {
            'private': '👤 Private Chat',
            'group': '👥 Group',
            'supergroup': '👥 Supergroup',
            'channel': '📢 Channel'
        }
        return types.get(chat_type, chat_type)

    def _send_message(self, chat_id, text):
        """Send message to Telegram"""
        url = f"{self.base_url}/sendMessage"
        payload = {
            'chat_id': chat_id,
            'text': text,
            'parse_mode': 'Markdown'
        }

        try:
            response = requests.post(url, json=payload)
            data = response.json()

            if data.get('ok'):
                print(f"✅ Sent message to {chat_id}")
                return True
            else:
                print(f"❌ Failed to send message: {data.get('description')}")
                return False

        except Exception as e:
            print(f"❌ Error sending message: {e}")
            return False

    def _answer_callback_query(self, callback_query_id):
        """Answer callback query (required)"""
        url = f"{self.base_url}/answerCallbackQuery"
        payload = {
            'callback_query_id': callback_query_id
        }

        try:
            requests.post(url, json=payload)
            print(f"✅ Answered callback query: {callback_query_id}")
        except Exception as e:
            print(f"❌ Error answering callback query: {e}")

    def set_webhook(self, url):
        """Set webhook for bot"""
        webhook_url = f"{self.base_url}/setWebhook"
        payload = {
            'url': url,
            'max_connections': 100
        }

        try:
            response = requests.post(webhook_url, json=payload)
            data = response.json()

            if data.get('ok'):
                print("✅ Webhook set successfully")
                return True
            else:
                print(f"❌ Failed to set webhook: {data.get('description')}")
                return False

        except Exception as e:
            print(f"❌ Error setting webhook: {e}")
            return False

    def delete_webhook(self):
        """Delete webhook"""
        url = f"{self.base_url}/deleteWebhook"

        try:
            response = requests.post(url)
            data = response.json()

            if data.get('ok'):
                print("✅ Webhook deleted successfully")
                return True
            else:
                print(f"❌ Failed to delete webhook: {data.get('description')}")
                return False

        except Exception as e:
            print(f"❌ Error deleting webhook: {e}")
            return False