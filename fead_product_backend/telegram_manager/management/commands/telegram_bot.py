# telegram_manager/management/commands/telegram_bot.py
from django.core.management.base import BaseCommand
import time
import requests
import logging
from django.conf import settings
from telegram_manager.bot_commands import TelegramBotCommands

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Run Telegram bot in polling mode'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🤖 Starting Telegram Bot...'))

        bot_commands = TelegramBotCommands()

        # Delete previous webhook (if exists)
        bot_commands.delete_webhook()

        self.stdout.write(self.style.SUCCESS('✅ Bot started in polling mode'))
        self.stdout.write('📡 Listening for messages...')
        self.stdout.write('💡 Send /get_id to bot in any chat to get chat ID')
        self.stdout.write('⏹️  Press Ctrl+C to stop')

        self._start_polling(bot_commands)

    def _start_polling(self, bot_commands):
        """Start polling for updates"""
        offset = 0

        while True:
            try:
                # Get updates
                updates = self._get_updates(bot_commands.bot_token, offset)

                if updates and 'result' in updates:
                    for update in updates['result']:
                        # Process update
                        bot_commands.process_update(update)
                        # Update offset for next update
                        offset = update['update_id'] + 1

                # Delay between requests
                time.sleep(1)

            except KeyboardInterrupt:
                self.stdout.write(self.style.WARNING('\n🛑 Bot stopped by user'))
                break
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'❌ Error in polling: {e}'))
                time.sleep(5)  # Longer delay on error

    def _get_updates(self, bot_token, offset):
        """Get updates from Telegram"""
        url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
        params = {
            'offset': offset,
            'timeout': 30,  # Longer timeout to reduce requests
            'allowed_updates': ['message', 'channel_post', 'callback_query']
        }

        try:
            response = requests.get(url, params=params, timeout=35)
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"❌ Request error: {e}")
            return None