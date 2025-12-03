# amazon_app/amazon_driver_manager.py
import logging
import time
import random
import re
from urllib.parse import urlparse, parse_qs
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains
from selenium_app.driver_manager import SeleniumDriverManager

logger = logging.getLogger(__name__)


class AmazonDriverManager:
    """مدیریت درایورهای مخصوص آمازون - کامپوزیشن به جای ارث‌بری"""

    def __init__(self):
        self.driver_manager = SeleniumDriverManager()
        self.country_drivers = {}  # {country_code: driver_instance}

    def get_amazon_driver(self, country_code, force_new=False):
        """دریافت درایور مخصوص کشور برای آمازون"""
        driver_name = f"amazon_{country_code.lower()}"

        if not force_new and country_code in self.country_drivers:
            driver = self.country_drivers[country_code]
            if self._is_driver_healthy(driver_name):
                logger.info(f"🚗 Using existing driver for {country_code}")
                return driver
            else:
                logger.info(f"🔄 Driver unhealthy, creating new one for {country_code}")
                self._cleanup_driver(driver_name)
                self.country_drivers.pop(country_code, None)

        # ایجاد درایور جدید با پروفایل مخصوص آمازون
        profile_data = {
            'headless': False,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'window_size': '1920,1080',
        }

        logger.info(f"🚗 Creating new Amazon driver for {country_code}")
        driver = self.driver_manager.get_or_create_driver(driver_name, 'CHROME', profile_data)
        self.country_drivers[country_code] = driver

        return driver

    def _is_driver_healthy(self, driver_name):
        """بررسی سلامت درایور"""
        return self.driver_manager._is_driver_healthy(driver_name)

    def _cleanup_driver(self, driver_name):
        """پاکسازی درایور مشکل‌دار"""
        self.driver_manager._cleanup_driver(driver_name)

    def safe_amazon_click(self, driver, by, value, timeout=10):
        """کلیک ایمن در آمازون با هندل کردن استثناها"""
        try:
            element = WebDriverWait(driver, timeout).until(
                EC.element_to_be_clickable((by, value))
            )
            element.click()
            time.sleep(1)  # تأخیر کوچک بعد از کلیک
            return True
        except Exception as e:
            logger.debug(f"Click failed on {value}: {e}")
            return False

    def safe_amazon_send_keys(self, driver, by, value, text, timeout=10):
        """ارسال متن ایمن در آمازون"""
        try:
            element = WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            element.clear()
            element.send_keys(text)
            return True
        except Exception as e:
            logger.debug(f"Send keys failed on {value}: {e}")
            return False

    def extract_asin_from_url(self, url):
        """استخراج ASIN از URL"""
        try:
            parsed_url = urlparse(url)
            path_parts = parsed_url.path.split('/')

            # از مسیر /dp/ASIN
            if 'dp' in path_parts:
                dp_index = path_parts.index('dp')
                if dp_index + 1 < len(path_parts):
                    asin = path_parts[dp_index + 1]
                    if len(asin) == 10 and asin.isalnum():
                        return asin.upper()

            # از پارامتر ASIN
            query_params = parse_qs(parsed_url.query)
            if 'asin' in query_params:
                asin = query_params['asin'][0]
                if len(asin) == 10 and asin.isalnum():
                    return asin.upper()

            return None
        except Exception as e:
            logger.error(f"Error extracting ASIN from URL: {e}")
            return None

    def simulate_human_behavior(self, driver):
        """شبیه‌سازی رفتار انسانی"""
        try:
            # اسکرول آرام
            for i in range(2):
                scroll_pixels = random.randint(300, 600)
                driver.execute_script(f"window.scrollTo(0, {scroll_pixels});")
                time.sleep(random.uniform(0.3, 1.0))

            # حرکت موس تصادفی
            actions = ActionChains(driver)
            actions.move_by_offset(random.randint(50, 150), random.randint(50, 100))
            actions.perform()
            time.sleep(0.5)

        except Exception as e:
            logger.debug(f"Human behavior simulation minor issue: {e}")

    def handle_amazon_block(self, driver):
        """مدیریت صفحات مسدودسازی آمازون"""
        try:
            page_text = driver.page_source.lower()
            automation_keywords = [
                "automated test software",
                "being controlled by automated test software",
                "bot behavior",
                "unusual traffic",
                "click the button below to continue"
            ]

            if any(keyword in page_text for keyword in automation_keywords):
                logger.warning("🛑 Amazon block page detected - attempting to bypass...")

                continue_button_selectors = [
                    "//button[contains(text(), 'Continue shopping')]",
                    "//a[contains(text(), 'Continue shopping')]",
                    "//input[@value='Continue shopping']",
                    "//button[contains(., 'Continue')]",
                    "//a[contains(., 'Continue')]"
                ]

                for selector in continue_button_selectors:
                    try:
                        continue_button = WebDriverWait(driver, 5).until(
                            EC.element_to_be_clickable((By.XPATH, selector))
                        )
                        continue_button.click()
                        logger.info("✅ Continue button clicked successfully")
                        time.sleep(3)
                        return True
                    except:
                        continue

                # اگر دکمه continue پیدا نشد، صفحه رو رفرش کن
                logger.warning("⚠️ Could not find continue button, trying refresh")
                driver.refresh()
                time.sleep(5)
                return True

            return True
        except Exception as e:
            logger.error(f"Error handling Amazon block: {e}")
            return False