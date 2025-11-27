# management/commands/test_selenium.py
from django.core.management.base import BaseCommand
from utils.selenium_helper import SeleniumHelper
import os


# management/commands/test_selenium.py
class Command(BaseCommand):
    def handle(self, *args, **options):
        helper = SeleniumHelper()
        try:
            self.stdout.write('🚀 Starting Selenium test...')
            self.stdout.write('👀 Watch the browser at: http://localhost:7900 (no password)')

            helper.init_driver()
            self.stdout.write('✅ Selenium driver initialized - you should see browser in VNC!')

            # تأخیر برای اینکه بتونی ببینی
            import time
            self.stdout.write('⏳ Waiting 5 seconds for you to watch VNC...')
            time.sleep(5)

            # تست با مراحل قابل مشاهده
            self.stdout.write('🌐 Navigating to frontend...')
            helper.driver.get('http://frontend:3000')
            time.sleep(3)  # می‌بینی صفحه لود میشه

            self.stdout.write('📸 Taking screenshot...')
            success = helper.take_screenshot('http://frontend:3000')

            if success:
                self.stdout.write(self.style.SUCCESS('✅ Test passed! Check VNC to see the browser.'))
            else:
                self.stdout.write(self.style.ERROR('❌ Screenshot failed'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error: {e}'))
        finally:
            helper.close()