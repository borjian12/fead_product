# amazon_app/geo_manager.py
import logging
import time
import re
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

logger = logging.getLogger(__name__)


class AmazonGeoManager:
    """مدیریت موقعیت جغرافیایی برای آمازون"""

    def __init__(self, driver_manager):
        self.driver_manager = driver_manager

    def configure_location(self, driver, country):
        """تنظیم موقعیت در آمازون فقط اگر نیاز باشد"""
        try:
            logger.info(f"🌍 Checking Amazon location for {country.name}")

            # 1. بررسی آیا در دامنه صحیح هستیم
            if not self._is_on_correct_domain(driver, country.amazon_domain):
                logger.info(f"🔄 Redirecting to correct domain: {country.amazon_domain}")
                amazon_url = f"https://www.{country.amazon_domain}"
                driver.get(amazon_url)
                time.sleep(3)
                self.driver_manager.handle_amazon_block(driver)

            # 2. بررسی و تنظیم ZIP Code اگر نیاز باشد
            zip_needed = country.default_zip_code and not self._is_zip_code_set(driver, country.default_zip_code)
            if zip_needed:
                success = self._set_amazon_zip_code(driver, country.default_zip_code)
                if not success:
                    logger.warning("⚠️ Failed to set ZIP code, but continuing...")
            else:
                logger.info("✅ ZIP code already set correctly")

            # 3. بررسی و تنظیم ارز اگر نیاز باشد
            if country.default_currency and not self._is_currency_set(driver, country.default_currency.code):
                currency_success = self._set_amazon_currency(driver, country.default_currency.code)
                if not currency_success:
                    logger.warning(f"⚠️ Failed to set currency to {country.default_currency.code}, but continuing...")
            else:
                currency_code = country.default_currency.code if country.default_currency else country.get_currency_code()
                logger.info(f"✅ Currency already set correctly to {currency_code}")

            logger.info(f"✅ Amazon location verified for {country.name}")
            return True

        except Exception as e:
            logger.error(f"❌ Error configuring Amazon location: {e}")
            return False

    def _is_on_correct_domain(self, driver, expected_domain):
        """بررسی آیا در دامنه صحیح آمازون هستیم"""
        try:
            current_url = driver.current_url
            return expected_domain in current_url
        except:
            return False

    def _is_zip_code_set(self, driver, expected_zip):
        """بررسی آیا ZIP Code صحیح ست شده"""
        try:
            # چک کردن دکمه موقعیت برای دیدن ZIP Code فعلی
            zip_element = driver.find_element(By.ID, "nav-global-location-popover-link")
            zip_text = zip_element.text.strip()

            # استخراج ZIP Code از متن
            zip_match = re.search(r'\b\d{5}\b', zip_text)
            if zip_match:
                current_zip = zip_match.group()
                logger.info(f"📮 Current ZIP code: {current_zip}, Expected: {expected_zip}")
                return current_zip == expected_zip

            return False
        except:
            return False

    def _is_currency_set(self, driver, expected_currency):
        """بررسی آیا ارز صحیح ست شده"""
        try:
            # روش 1: بررسی از طریق المنت‌های صفحه
            currency_indicators = [
                "//*[contains(text(), '$')]" if expected_currency == "USD" else None,
                "//*[contains(text(), '€')]" if expected_currency == "EUR" else None,
                "//*[contains(text(), '£')]" if expected_currency == "GBP" else None,
                "//*[contains(text(), '¥')]" if expected_currency == "JPY" else None,
                "//*[contains(text(), 'C$')]" if expected_currency == "CAD" else None,
                "//*[contains(text(), 'A$')]" if expected_currency == "AUD" else None,
            ]

            # حذف مقادیر None
            currency_indicators = [indicator for indicator in currency_indicators if indicator]

            for indicator in currency_indicators:
                try:
                    elements = driver.find_elements(By.XPATH, indicator)
                    if elements:
                        logger.info(f"✅ Currency verified: {expected_currency}")
                        return True
                except:
                    continue

            # روش 2: بررسی از طریق URL یا المنت‌های خاص
            try:
                # چک کردن المنت‌های قیمت
                price_elements = driver.find_elements(By.CSS_SELECTOR, ".a-price-symbol, .a-price-whole")
                for element in price_elements:
                    text = element.text.strip()
                    currency_symbols = {
                        'USD': ['$', 'US$'],
                        'EUR': ['€'],
                        'GBP': ['£'],
                        'JPY': ['¥', '￥'],
                        'CAD': ['C$', 'CA$'],
                        'AUD': ['A$', 'AU$']
                    }

                    symbols = currency_symbols.get(expected_currency, [])
                    for symbol in symbols:
                        if symbol in text:
                            logger.info(f"✅ Currency verified via price symbol: {expected_currency} ({symbol})")
                            return True
            except:
                pass

            logger.info(f"🔍 Currency not detected as set: {expected_currency}")
            return False

        except Exception as e:
            logger.error(f"❌ Error checking currency: {e}")
            return False

    def _set_amazon_zip_code(self, driver, zip_code):
        """تنظیم ZIP Code در آمازون"""
        try:
            logger.info(f"📮 Setting ZIP code: {zip_code}")

            # کلیک روی دکمه موقعیت
            if not self.driver_manager.safe_amazon_click(driver, By.ID, "nav-global-location-popover-link"):
                return False

            time.sleep(1)

            # وارد کردن ZIP جدید
            if not self.driver_manager.safe_amazon_send_keys(driver, By.ID, "GLUXZipUpdateInput", zip_code):
                return False

            # اعمال تغییرات
            if not self.driver_manager.safe_amazon_click(driver, By.ID, "GLUXZipUpdate"):
                return False

            time.sleep(2)

            # تأیید تغییر موقعیت
            try:
                continue_button = driver.find_element(By.CSS_SELECTOR, "span[data-action='a-popover-close']")
                continue_button.click()
            except:
                pass

            logger.info(f"✅ ZIP code set to: {zip_code}")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to set ZIP code: {e}")
            return False

    def _set_amazon_currency(self, driver, currency_code):
        """تنظیم ارز در آمازون"""
        try:
            logger.info(f"💰 Setting currency to: {currency_code}")

            # اول چک کنیم که واقعاً نیاز به تغییر داریم
            if self._is_currency_set(driver, currency_code):
                logger.info(f"✅ Currency already set to {currency_code}, skipping...")
                return True

            # رفتن به صفحه تنظیمات ارز
            current_domain = driver.current_url.split('/')[2]
            currency_url = f"https://www.{current_domain}/gp/help/customer/display.html?nodeId=201895280"
            driver.get(currency_url)
            time.sleep(2)

            # جستجوی ارز مورد نظر
            currency_dropdown = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "a-native-dropdown"))
            )

            # انتخاب ارز مورد نظر
            from selenium.webdriver.support.ui import Select
            dropdown = Select(currency_dropdown)
            dropdown.select_by_value(currency_code)

            time.sleep(1)

            # ذخیره تغییرات
            save_button = driver.find_element(By.CSS_SELECTOR, "input[type='submit']")
            save_button.click()

            time.sleep(2)

            # تأیید که ارز واقعاً ست شده
            if self._is_currency_set(driver, currency_code):
                logger.info(f"✅ Currency successfully set to: {currency_code}")
                return True
            else:
                logger.warning(f"⚠️ Currency setting may have failed: {currency_code}")
                return False

        except Exception as e:
            logger.error(f"❌ Failed to set currency {currency_code}: {e}")

            # روش جایگزین: استفاده از صفحه تنظیمات
            try:
                return self._set_currency_alternative_method(driver, currency_code)
            except Exception as alt_e:
                logger.error(f"❌ Alternative currency setting also failed: {alt_e}")
                return False

    def _set_currency_alternative_method(self, driver, currency_code):
        """روش جایگزین برای تنظیم ارز"""
        try:
            logger.info(f"🔄 Trying alternative currency setting method for: {currency_code}")

            # رفتن به صفحه اصلی تنظیمات
            current_domain = driver.current_url.split('/')[2]
            settings_url = f"https://www.{current_domain}/gp/customer-preferences/select-currency"
            driver.get(settings_url)
            time.sleep(2)

            # انتخاب ارز
            currency_option = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, f"input[name='currency'][value='{currency_code}']"))
            )
            currency_option.click()

            # تأیید انتخاب
            confirm_button = driver.find_element(By.CSS_SELECTOR, "input[type='submit']")
            confirm_button.click()

            time.sleep(2)

            # تأیید نهایی
            if self._is_currency_set(driver, currency_code):
                logger.info(f"✅ Currency set to {currency_code} (alternative method)")
                return True
            else:
                logger.warning(f"⚠️ Alternative currency method may have failed: {currency_code}")
                return False

        except Exception as e:
            logger.error(f"❌ Alternative currency method failed: {e}")
            return False