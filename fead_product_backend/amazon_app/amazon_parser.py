# amazon_app/amazon_parser.py
import re
import json
import logging
import random
import time
from urllib.parse import urlparse, parse_qs
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains

logger = logging.getLogger(__name__)


class AmazonPageParser:
    def __init__(self, driver):
        self.driver = driver
        self.wait = WebDriverWait(driver, 15)
        self.current_domain = "amazon.com"
        self.geo_settings = {
            'country': 'US',
            'zip_code': '10001',
            'city': 'New York',
            'state': 'NY'
        }
        self.language = "en-US"
        self.location_configured = False  # 🔥 فلگ برای جلوگیری از تنظیم مکرر

    def set_language(self, language):
        """تنظیم زبان"""
        self.language = language
        logger.info(f"🔤 Language set to: {language}")

    def set_geo_location(self, country='US', zip_code='10001', city='New York', state='NY'):
        """
        تنظیم موقعیت جغرافیایی برای مشاهده قیمت و موجودی مناسب
        """
        self.geo_settings = {
            'country': country,
            'zip_code': zip_code,
            'city': city,
            'state': state
        }

        # تنظیم دامنه بر اساس کشور
        country_domain_map = {
            'US': 'amazon.com',
            'DE': 'amazon.de',
            'GB': 'amazon.co.uk',
            'FR': 'amazon.fr',
            'IT': 'amazon.it',
            'ES': 'amazon.es',
            'CA': 'amazon.ca',
            'JP': 'amazon.co.jp',
            'IN': 'amazon.in',
            'AU': 'amazon.com.au',
            'BR': 'amazon.com.br',
            'MX': 'amazon.com.mx'
        }

        self.current_domain = country_domain_map.get(country, 'amazon.com')
        logger.info(f"🌍 Geo location set to: {country}, {city}, {zip_code}")
        logger.info(f"🌐 Domain set to: {self.current_domain}")

    def navigate_to_product(self, product_identifier):
        """
        رفتن به صفحه محصول با اعمال تنظیمات جغرافیایی از طریق کوکی
        """
        try:
            # تشخیص نوع شناسه ورودی
            if self._is_url(product_identifier):
                product_url = product_identifier
                asin = self._extract_asin_from_url(product_url)
                logger.info(f"🔄 Using direct product URL: {product_url}")
            else:
                asin = product_identifier.upper()
                product_url = f"https://www.{self.current_domain}/dp/{asin}"
                logger.info(f"🔄 Using ASIN to build URL: {product_url}")

            # استخراج دامنه از URL (اگر لینک مستقیم بود)
            if self._is_url(product_identifier):
                domain = self._extract_domain_from_url(product_identifier)
                if domain:
                    self.current_domain = domain

            logger.info(f"🔄 Navigating to: {product_url}")
            self.driver.get(product_url)

            # منتظر لود شدن صفحه
            self.wait.until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )

            # 🔥 مدیریت اتوماسیون بلاک
            if self._handle_automation_block():
                logger.info("✅ Automation block handled successfully")

            # 🔥 تنظیم موقعیت جغرافیایی از طریق کوکی (فقط یکبار)
            if not self.location_configured:
                self._set_geo_cookies()
                self.location_configured = True

            # چک کردن redirectها و صفحات خطا
            current_url = self.driver.current_url
            if self._is_error_page(current_url):
                logger.warning("❌ Amazon blocked the request or page not found")
                return False

            # شبیه‌سازی رفتار انسانی
            self._simulate_human_behavior()

            return True

        except Exception as e:
            logger.error(f"❌ Navigation failed: {e}")
            return False

    def _set_geo_cookies(self):
        """تنظیم کامل موقعیت جغرافیایی از طریق کوکی‌ها"""
        try:
            # حذف کوکی‌های قدیمی
            self._clear_existing_cookies()

            # تنظیم کوکی‌های اصلی موقعیت
            self._set_core_geo_cookies()

            # تنظیم کوکی‌های پیشرفته موقعیت
            self._set_advanced_geo_cookies()

            # تنظیم کوکی‌های زبان
            self._set_language_cookies()

            logger.info(f"🍪 Geo cookies set for {self.geo_settings['country']} - {self.geo_settings['zip_code']}")
            return True

        except Exception as e:
            logger.error(f"❌ Error setting geo cookies: {e}")
            return False

    def _clear_existing_cookies(self):
        """پاک کردن کوکی‌های موجود مربوط به موقعیت"""
        cookies_to_remove = [
            'session-id', 'session-id-time', 'ubid-main', 'x-main',
            'session-token', 'lc-main', 'i18n-prefs', 'sp-cdn',
            'csm-hit', 'skin', 'uis', 'x-wl-uid'
        ]

        for cookie_name in cookies_to_remove:
            try:
                self.driver.delete_cookie(cookie_name)
            except:
                pass

    def _set_core_geo_cookies(self):
        """تنظیم کوکی‌های اصلی موقعیت"""
        core_cookies = [
            {
                'name': 'session-id',
                'value': f"{self.geo_settings['country'].lower()}-{random.randint(1000000, 9999999)}",
                'domain': f'.{self.current_domain}',
                'path': '/',
                'secure': True
            },
            {
                'name': 'ubid-main',
                'value': f"{self.geo_settings['country']}{random.randint(100, 999)}",
                'domain': f'.{self.current_domain}',
                'path': '/',
                'secure': True
            },
            {
                'name': 'x-main',
                'value': f"{self.geo_settings['country']}{random.randint(1000, 9999)}",
                'domain': f'.{self.current_domain}',
                'path': '/',
                'secure': True
            }
        ]

        for cookie in core_cookies:
            try:
                self.driver.add_cookie(cookie)
            except Exception as e:
                logger.debug(f"Failed to set cookie {cookie['name']}: {e}")

    def _set_advanced_geo_cookies(self):
        """تنظیم کوکی‌های پیشرفته موقعیت"""
        advanced_cookies = [
            {
                'name': 'session-id-time',
                'value': str(int(time.time())),
                'domain': f'.{self.current_domain}',
                'path': '/'
            },
            {
                'name': 'lc-main',
                'value': json.dumps({
                    'country': self.geo_settings['country'],
                    'zip': self.geo_settings['zip_code'],
                    'city': self.geo_settings['city'],
                    'state': self.geo_settings['state']
                }),
                'domain': f'.{self.current_domain}',
                'path': '/'
            },
            {
                'name': 'session-token',
                'value': f"token_{random.randint(1000000000, 9999999999)}",
                'domain': f'.{self.current_domain}',
                'path': '/',
                'secure': True
            }
        ]

        for cookie in advanced_cookies:
            try:
                self.driver.add_cookie(cookie)
            except Exception as e:
                logger.debug(f"Failed to set advanced cookie {cookie['name']}: {e}")

    def _set_language_cookies(self):
        """تنظیم کوکی‌های زبان"""
        language_cookies = [
            {
                'name': 'i18n-prefs',
                'value': self._get_currency_for_country(),
                'domain': f'.{self.current_domain}',
                'path': '/'
            },
            {
                'name': 'lc-main',
                'value': json.dumps({
                    'language': self.language,
                    'currency': self._get_currency_for_country(),
                    'country': self.geo_settings['country']
                }),
                'domain': f'.{self.current_domain}',
                'path': '/'
            }
        ]

        for cookie in language_cookies:
            try:
                self.driver.add_cookie(cookie)
            except Exception as e:
                logger.debug(f"Failed to set language cookie {cookie['name']}: {e}")

    def _get_currency_for_country(self):
        """دریافت ارز بر اساس کشور"""
        currency_map = {
            'US': 'USD', 'GB': 'GBP', 'DE': 'EUR', 'FR': 'EUR', 'IT': 'EUR',
            'ES': 'EUR', 'CA': 'CAD', 'AU': 'AUD', 'JP': 'JPY', 'IN': 'INR',
            'BR': 'BRL', 'MX': 'MXN'
        }
        return currency_map.get(self.geo_settings['country'], 'USD')

    def _handle_automation_block(self):
        """
        مدیریت صفحه مسدودسازی اتوماسیون
        """
        try:
            page_text = self.driver.page_source.lower()
            automation_keywords = [
                "automated test software",
                "being controlled by automated test software",
                "bot behavior",
                "unusual traffic",
                "click the button below to continue"
            ]

            if any(keyword in page_text for keyword in automation_keywords):
                logger.warning("🛑 Automation block page detected - attempting to click continue button")

                continue_button_selectors = [
                    "//button[contains(text(), 'Continue shopping')]",
                    "//a[contains(text(), 'Continue shopping')]",
                    "//input[@value='Continue shopping']",
                    "//*[contains(@class, 'continue') and contains(text(), 'shopping')]",
                    "//button[contains(., 'Continue')]",
                    "//a[contains(., 'Continue')]"
                ]

                for selector in continue_button_selectors:
                    try:
                        continue_button = WebDriverWait(self.driver, 8).until(
                            EC.element_to_be_clickable((By.XPATH, selector))
                        )

                        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", continue_button)
                        time.sleep(random.uniform(1, 2))

                        continue_button.click()
                        logger.info("✅ Continue button clicked successfully")

                        time.sleep(random.uniform(3, 5))

                        if self._is_product_page_loaded():
                            logger.info("🎯 Successfully bypassed automation block")
                            return True
                        else:
                            self.driver.refresh()
                            time.sleep(random.uniform(2, 4))
                            return True

                    except TimeoutException:
                        continue
                    except Exception as e:
                        logger.debug(f"Failed with selector {selector}: {e}")
                        continue

                logger.warning("⚠️ Could not find continue button, trying refresh")
                self.driver.refresh()
                time.sleep(random.uniform(3, 6))
                return False

            return True

        except Exception as e:
            logger.error(f"❌ Error handling automation block: {e}")
            return False

    def _simulate_human_behavior(self):
        """شبیه‌سازی رفتار انسانی"""
        try:
            # اسکرول آرام
            for i in range(3):
                scroll_pixels = random.randint(300, 800)
                self.driver.execute_script(f"window.scrollTo(0, {scroll_pixels});")
                time.sleep(random.uniform(0.5, 1.5))

            # حرکت موس تصادفی
            actions = ActionChains(self.driver)
            actions.move_by_offset(random.randint(50, 200), random.randint(50, 150))
            actions.perform()
            time.sleep(1)

        except Exception as e:
            logger.debug(f"Human behavior simulation minor issue: {e}")

    # 🔥 حذف متدهای مربوط به پاپ‌آپ آدرس
    # _set_delivery_location, _fill_delivery_popup, _set_delivery_via_url حذف شدند

    def get_product_data(self):
        """استخراج اطلاعات محصول با در نظر گرفتن موقعیت جغرافیایی"""
        try:
            if not self._is_product_page_loaded():
                logger.warning("❌ Product page not properly loaded")
                return None

            asin = self._extract_asin()
            if not asin:
                logger.warning("❌ Could not extract ASIN")
                return None

            # استخراج داده‌های اصلی
            product_data = {
                'asin': asin,
                'domain': self.current_domain,
                'geo_location': self.geo_settings.copy(),
                'title': self._extract_title(),
                'price': self._extract_price(),
                'currency': self._extract_currency(),
                'rating': self._extract_rating(),
                'review_count': self._extract_review_count(),
                'brand': self._extract_brand(),
                'image_url': self._extract_image_url(),
                'availability': self._extract_availability(),
                'seller': self._extract_seller(),
                'shipping_info': self._extract_shipping_info(),
                'delivery_date': self._extract_delivery_date(),
                'variants': self._extract_variant_asins(),
            }

            # استخراج داده‌های اختیاری
            optional_data = {
                'description': self._extract_description(),
                'features': self._extract_features(),
                'specifications': self._extract_specifications(),
                'category': self._extract_category(),
                'condition': self._extract_condition(),
            }

            for key, value in optional_data.items():
                if value:
                    product_data[key] = value

            logger.info(f"✅ Successfully extracted data for ASIN: {asin} from {self.geo_settings['city']}, {self.geo_settings['country']}")
            logger.info(f"📦 Found {len(product_data['variants'])} variant ASINs")
            return product_data

        except Exception as e:
            logger.error(f"❌ Error extracting product data: {e}")
            return None

    # سایر متدهای استخراج داده بدون تغییر می‌مانند
    def _extract_currency(self):
        """استخراج واحد پول بر اساس دامنه و موقعیت"""
        return self._get_currency_for_country()

    def _is_url(self, text):
        try:
            result = urlparse(text)
            return all([result.scheme, result.netloc])
        except:
            return False

    def _extract_domain_from_url(self, url):
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            if 'amazon.' in domain:
                domain_parts = domain.split('.')
                if len(domain_parts) >= 2:
                    return f"{domain_parts[-2]}.{domain_parts[-1]}"
            return "amazon.com"
        except:
            return "amazon.com"

    def _is_error_page(self, url):
        error_indicators = [
            'sorry', 'errors', 'bot', 'automated', 'captcha',
            'page-not-found', 'error', 'unavailable'
        ]
        url_lower = url.lower()
        return any(indicator in url_lower for indicator in error_indicators)

    def set_domain(self, domain):
        if domain and 'amazon.' in domain:
            self.current_domain = domain
            logger.info(f"🌐 Domain set to: {self.current_domain}")
        else:
            logger.warning(f"⚠️ Invalid domain: {domain}, using default: {self.current_domain}")

    def get_current_domain(self):
        return self.current_domain

    def navigate_to_product_page(self, asin):
        logger.warning("⚠️ Using deprecated method navigate_to_product_page(), use navigate_to_product() instead")
        return self.navigate_to_product(asin)

    def _extract_delivery_date(self):
        """استخراج تاریخ تحویل بر اساس موقعیت جغرافیایی"""
        try:
            delivery_selectors = [
                '#mir-layout-DELIVERY_BLOCK-slot-DELIVERY_MESSAGE',
                '.a-section.delivery-block-message',
                '#ddmDeliveryMessage',
                '.shipping-speeds',
                '[data-csa-c-delivery-time]'
            ]

            for selector in delivery_selectors:
                try:
                    element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    delivery_text = element.text.strip()
                    if delivery_text and len(delivery_text) > 5:
                        return delivery_text
                except:
                    continue
            return ""
        except:
            return ""

    def _extract_variant_asins(self):
        """استخراج variant ASIN ها از صفحه محصول"""
        variants = []
        try:
            # روش ۱: از بخش twister (variation)
            twister_selectors = [
                'ul[class*="dimension-values-list"] li[data-asin]',
                'ul[class*="a-button-list"] li[data-asin]',
                'ul[class*="twister"] li[data-asin]',
                '.swatch-list-item-text[data-asin]',
                '.inline-twister-swatch[data-asin]'
            ]

            for selector in twister_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        variant_data = self._extract_twister_variant(element)
                        if variant_data and variant_data not in variants:
                            variants.append(variant_data)
                    if elements:
                        logger.info(f"🔍 Found {len(elements)} variants using selector: {selector}")
                        break
                except Exception as e:
                    logger.debug(f"Selector {selector} failed: {e}")
                    continue

            # روش ۲: از سایر بخش‌ها
            if not variants:
                other_selectors = [
                    '[data-asin]',
                    '.a-button-toggle[data-asin]',
                    '.swatchAvailable[data-asin]'
                ]

                for selector in other_selectors:
                    try:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        for element in elements:
                            variant_data = self._extract_basic_variant(element)
                            if variant_data and variant_data not in variants:
                                variants.append(variant_data)
                    except:
                        continue

            # حذف duplicate ها بر اساس ASIN
            unique_variants = []
            seen_asins = set()
            for variant in variants:
                if variant['asin'] and variant['asin'] not in seen_asins:
                    seen_asins.add(variant['asin'])
                    unique_variants.append(variant)

            logger.info(f"📦 Extracted {len(unique_variants)} unique variant ASINs")
            return unique_variants

        except Exception as e:
            logger.error(f"❌ Error extracting variant ASINs: {e}")
            return []

    def _extract_twister_variant(self, element):
        """استخراج اطلاعات variant از بخش twister"""
        try:
            # استخراج ASIN
            asin = element.get_attribute('data-asin')
            if not asin or len(asin) != 10:
                return None

            variant_data = {
                'asin': asin.upper(),
                'type': 'style',
                'value': '',
                'url': f"https://www.{self.current_domain}/dp/{asin}",
                'image_url': '',
                'price': None,
                'original_price': None,
                'availability': True
            }

            # استخراج نام variant
            try:
                title_element = element.find_element(By.CSS_SELECTOR, '.swatch-title-text')
                variant_data['value'] = title_element.text.strip()
            except:
                try:
                    aria_element = element.find_element(By.CSS_SELECTOR, '[aria-labelledby]')
                    aria_id = aria_element.get_attribute('aria-labelledby')
                    if aria_id:
                        label_element = self.driver.find_element(By.ID, f"{aria_id}-announce")
                        variant_data['value'] = label_element.text.strip()
                except:
                    pass

            # استخراج قیمت فعلی
            try:
                price_element = element.find_element(By.CSS_SELECTOR, '.a-price .a-offscreen')
                price_text = price_element.get_attribute('textContent') or price_element.text
                price_match = re.search(r'[\d,]+\.?\d*', price_text.replace(',', ''))
                if price_match:
                    variant_data['price'] = float(price_match.group())
            except:
                pass

            # استخراج قیمت اصلی (قیمت قبل از تخفیف)
            try:
                original_price_element = element.find_element(By.CSS_SELECTOR, '.a-text-price .a-offscreen')
                original_price_text = original_price_element.get_attribute('textContent') or original_price_element.text
                original_price_match = re.search(r'[\d,]+\.?\d*', original_price_text.replace(',', ''))
                if original_price_match:
                    variant_data['original_price'] = float(original_price_match.group())
            except:
                pass

            # استخراج وضعیت موجودی
            try:
                availability_element = element.find_element(By.CSS_SELECTOR, '.a-color-success')
                availability_text = availability_element.text.strip().lower()
                if 'out of stock' in availability_text or 'unavailable' in availability_text:
                    variant_data['availability'] = False
            except:
                pass

            # استخراج تصویر
            try:
                img_element = element.find_element(By.TAG_NAME, 'img')
                variant_data['image_url'] = img_element.get_attribute('src')
            except:
                pass

            return variant_data

        except Exception as e:
            logger.debug(f"Could not extract twister variant: {e}")
            return None

    def _extract_basic_variant(self, element):
        """استخراج اطلاعات variant پایه"""
        try:
            asin = element.get_attribute('data-asin')
            if not asin or len(asin) != 10:
                return None

            return {
                'asin': asin.upper(),
                'type': 'variant',
                'value': '',
                'url': f"https://www.{self.current_domain}/dp/{asin}",
                'image_url': '',
                'price': None,
                'original_price': None,
                'availability': True
            }
        except:
            return None

    def _is_product_page_loaded(self):
        """چک کردن آیا صفحه محصول درست لود شده"""
        try:
            # چک کردن المنت‌های اصلی صفحه محصول
            indicators = [
                '#dp',  # container اصلی محصول
                '#productTitle',  # عنوان محصول
                '#landingImage',  # تصویر محصول
            ]

            for indicator in indicators:
                try:
                    self.driver.find_element(By.CSS_SELECTOR, indicator)
                    return True
                except:
                    continue

            # اگر المنت‌های اصلی پیدا نشدند
            logger.warning("❌ Product page elements not found")
            return False

        except Exception as e:
            logger.error(f"❌ Error checking page load: {e}")
            return False

    def _extract_asin(self):
        """استخراج ASIN از صفحه"""
        try:
            # روش ۱: از URL
            current_url = self.driver.current_url
            asin_from_url = self._extract_asin_from_url(current_url)
            if asin_from_url:
                return asin_from_url

            # روش ۲: از data attributes
            asin_selectors = [
                '[data-asin]',
                '[data-product-asin]',
                '#ASIN',
            ]

            for selector in asin_selectors:
                try:
                    element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    asin = element.get_attribute('data-asin') or element.get_attribute(
                        'data-product-asin') or element.get_attribute('value')
                    if asin and len(asin) == 10:
                        return asin.upper()
                except:
                    continue

            return None

        except Exception as e:
            logger.error(f"❌ Error extracting ASIN: {e}")
            return None

    def _extract_asin_from_url(self, url):
        """استخراج ASIN از URL"""
        try:
            parsed_url = urlparse(url)
            path_parts = parsed_url.path.split('/')

            # پیدا کردن /dp/ASIN در مسیر
            if 'dp' in path_parts:
                dp_index = path_parts.index('dp')
                if dp_index + 1 < len(path_parts):
                    asin = path_parts[dp_index + 1]
                    if len(asin) == 10 and asin.isalnum():
                        return asin.upper()

            # پیدا کردن در query parameters
            query_params = parse_qs(parsed_url.query)
            if 'asin' in query_params:
                asin = query_params['asin'][0]
                if len(asin) == 10 and asin.isalnum():
                    return asin.upper()

            return None

        except Exception as e:
            logger.error(f"❌ Error extracting ASIN from URL: {e}")
            return None

    def _extract_title(self):
        """استخراج عنوان محصول"""
        title_selectors = [
            '#productTitle',
            '#title',
            '.product-title-word-break',
            'h1.a-size-large',
        ]

        for selector in title_selectors:
            try:
                element = self.driver.find_element(By.CSS_SELECTOR, selector)
                title = element.text.strip()
                if title and len(title) > 5:
                    return title
            except:
                continue
        return ""

    def _extract_price(self):
        """استخراج قیمت"""
        price_selectors = [
            '.a-price-whole',
            '.a-price .a-offscreen',
            '#priceblock_dealprice',
            '#priceblock_ourprice',
            '.a-price-current',
            '[data-a-color="price"] .a-offscreen',
        ]

        for selector in price_selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    price_text = element.text.strip()
                    # استخراج عدد از متن قیمت
                    price_match = re.search(r'[\d,]+\.?\d*', price_text.replace(',', ''))
                    if price_match:
                        return float(price_match.group())
            except:
                continue
        return None

    def _extract_rating(self):
        """استخراج امتیاز"""
        rating_selectors = [
            '[data-hook="average-star-rating"] .a-icon-alt',
            '.a-star-4-5',
            '#acrPopover',
            '.a-icon-star .a-icon-alt',
        ]

        for selector in rating_selectors:
            try:
                element = self.driver.find_element(By.CSS_SELECTOR, selector)
                rating_text = element.text.strip()
                rating_match = re.search(r'(\d+\.?\d*) out of 5', rating_text)
                if rating_match:
                    return float(rating_match.group(1))
            except:
                continue
        return None

    def _extract_review_count(self):
        """استخراج تعداد نظرات"""
        review_selectors = [
            '#acrCustomerReviewText',
            '[data-hook="total-review-count"]',
            '.averageStarRatingNumerical',
        ]

        for selector in review_selectors:
            try:
                element = self.driver.find_element(By.CSS_SELECTOR, selector)
                review_text = element.text.strip()
                review_match = re.search(r'([\d,]+)', review_text.replace(',', ''))
                if review_match:
                    return int(review_match.group(1))
            except:
                continue
        return 0

    def _extract_brand(self):
        """استخراج برند"""
        brand_selectors = [
            '#bylineInfo',
            '#brand',
            '.a-link-normal[href*="/s?k="]',
            '#productOverview_feature_div tr:contains("Brand") td',
        ]

        for selector in brand_selectors:
            try:
                element = self.driver.find_element(By.CSS_SELECTOR, selector)
                brand_text = element.text.strip()
                if brand_text:
                    # پاک کردن متن‌های اضافی
                    clean_brand = brand_text.replace('Visit the', '').replace('Store', '').replace('Brand:', '').strip()
                    if clean_brand and len(clean_brand) > 1:
                        return clean_brand
            except:
                continue
        return ""

    def _extract_image_url(self):
        """استخراج URL تصویر"""
        image_selectors = [
            '#landingImage',
            '#imgBlkFront',
            '.a-dynamic-image',
            '[data-old-hires]',
        ]

        for selector in image_selectors:
            try:
                element = self.driver.find_element(By.CSS_SELECTOR, selector)
                image_url = element.get_attribute('src') or element.get_attribute('data-old-hires')
                if image_url and 'http' in image_url:
                    return image_url
            except:
                continue
        return ""

    def _extract_availability(self):
        """استخراج وضعیت موجودی"""
        availability_indicators = [
            '#availability .a-color-success',
            '#availability span',
            '.a-size-medium.a-color-success',
            '#outOfStock',
        ]

        for selector in availability_indicators:
            try:
                element = self.driver.find_element(By.CSS_SELECTOR, selector)
                availability_text = element.text.strip().lower()
                if 'in stock' in availability_text or 'available' in availability_text:
                    return True
                elif 'out of stock' in availability_text or 'unavailable' in availability_text:
                    return False
            except:
                continue
        return True  # فرض بر موجود بودن

    def _extract_seller(self):
        """استخراج فروشنده"""
        seller_selectors = [
            '#merchant-info',
            '#sellerProfileTriggerId',
            '#fulfillmentCenterFeature .a-size-small',
        ]

        for selector in seller_selectors:
            try:
                element = self.driver.find_element(By.CSS_SELECTOR, selector)
                seller_text = element.text.strip()
                if 'sold by' in seller_text.lower():
                    return seller_text.replace('Sold by:', '').replace('and fulfilled by Amazon', '').strip()
                elif 'amazon' in seller_text.lower():
                    return 'Amazon'
            except:
                continue
        return "Amazon"

    def _extract_description(self):
        """استخراج توضیحات محصول"""
        try:
            desc_selectors = [
                '#productDescription',
                '.product-description',
                '#aplus',
                '.aplus-v2'
            ]

            for selector in desc_selectors:
                try:
                    element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    description = element.text.strip()
                    if description and len(description) > 50:
                        return description
                except:
                    continue
            return ""
        except:
            return ""

    def _extract_features(self):
        """استخراج ویژگی‌های محصول"""
        try:
            features = []
            feature_selectors = [
                '#feature-bullets .a-list-item',
                '.a-unordered-list .a-list-item',
                '[data-hook="cr-features-list"] li'
            ]

            for selector in feature_selectors:
                try:
                    feature_elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in feature_elements:
                        text = element.text.strip()
                        if text and len(text) > 10 and not text.startswith('#'):
                            features.append(text)
                    if features:
                        break
                except:
                    continue
            return features
        except:
            return []

    def _extract_specifications(self):
        """استخراج مشخصات فنی محصول"""
        try:
            specs = {}

            # روش ۱: جدول مشخصات فنی
            spec_selectors = [
                '.prodDetTable tr',
                '.product-specification-table tr',
                '#productDetails_detailBullets_sections1 tr'
            ]

            for selector in spec_selectors:
                try:
                    spec_rows = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for row in spec_rows:
                        try:
                            cells = row.find_elements(By.TAG_NAME, 'td')
                            if len(cells) == 2:
                                key = cells[0].text.strip().rstrip(':')
                                value = cells[1].text.strip()
                                if key and value:
                                    specs[key] = value
                        except:
                            continue
                    if specs:
                        break
                except:
                    continue

            # روش ۲: بخش technical details
            if not specs:
                try:
                    tech_details = self.driver.find_element(By.CSS_SELECTOR, '#technicalSpecifications_section_1')
                    rows = tech_details.find_elements(By.TAG_NAME, 'tr')
                    for row in rows:
                        try:
                            th = row.find_element(By.TAG_NAME, 'th')
                            td = row.find_element(By.TAG_NAME, 'td')
                            key = th.text.strip().rstrip(':')
                            value = td.text.strip()
                            if key and value:
                                specs[key] = value
                        except:
                            continue
                except:
                    pass

            return specs
        except:
            return {}

    def _extract_category(self):
        """استخراج دسته‌بندی محصول"""
        try:
            categories = []

            # روش ۱: breadcrumbs
            breadcrumb_selectors = [
                '#wayfinding-breadcrumbs_container a',
                '.a-breadcrumb li a',
                '[aria-label="breadcrumb"] a'
            ]

            for selector in breadcrumb_selectors:
                try:
                    breadcrumbs = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for crumb in breadcrumbs:
                        text = crumb.text.strip()
                        if text and text not in ['Home', '›']:
                            categories.append(text)
                    if categories:
                        break
                except:
                    continue

            return ' > '.join(categories) if categories else ""
        except:
            return ""

    def _extract_shipping_info(self):
        """استخراج اطلاعات حمل و نقل"""
        try:
            shipping_selectors = [
                '#mir-layout-DELIVERY_BLOCK-slot-DELIVERY_MESSAGE',
                '.shipping-weight',
                '.a-section.shipping-weight'
            ]

            for selector in shipping_selectors:
                try:
                    element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    shipping_text = element.text.strip()
                    if shipping_text and len(shipping_text) > 10:
                        return shipping_text
                except:
                    continue
            return ""
        except:
            return ""

    def _extract_condition(self):
        """استخراج وضعیت محصول"""
        try:
            condition_selectors = [
                '#condition',
                '.a-section.condition',
                '[data-feature-name="productOverview"] .a-span9'
            ]

            for selector in condition_selectors:
                try:
                    element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    condition_text = element.text.strip().lower()
                    if 'new' in condition_text:
                        return 'NEW'
                    elif 'used' in condition_text:
                        return 'USED'
                    elif 'renewed' in condition_text or 'refurbished' in condition_text:
                        return 'RENEWED'
                except:
                    continue

            # روش ۲: از عنوان صفحه
            try:
                page_title = self.driver.title.lower()
                if 'renewed' in page_title or 'refurbished' in page_title:
                    return 'RENEWED'
                elif 'used' in page_title:
                    return 'USED'
            except:
                pass

            return 'NEW'  # پیش‌فرض
        except:
            return 'NEW'

    def reset_location_config(self):
        """بازنشانی تنظیمات موقعیت (برای استفاده مجدد از پارسر)"""
        self.location_configured = False
        logger.info("🔄 Location configuration reset")

    def close(self):
        """بستن درایور"""
        try:
            if self.driver:
                self.driver.quit()
                logger.info("🔴 Driver closed")
        except Exception as e:
            logger.error(f"❌ Error closing driver: {e}")
