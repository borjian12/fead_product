# amazon_app/amazon_parser.py
import logging
import time
import re
from urllib.parse import urlparse
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

logger = logging.getLogger(__name__)


class AmazonProductParser:
    def __init__(self, driver_manager, driver, country):
        self.driver_manager = driver_manager
        self.driver = driver
        self.country = country
        self.wait = WebDriverWait(driver, 15)

    def crawl_product_by_url(self, product_url):
        """کراول کردن صفحه محصول با URL"""
        try:
            logger.info(f"🔄 Crawling product from URL: {product_url}")

            # لود صفحه
            self.driver.get(product_url)
            time.sleep(3)

            # هندل کردن بلاک
            self.driver_manager.handle_amazon_block(self.driver)

            # شبیه‌سازی رفتار انسانی
            self.driver_manager.simulate_human_behavior(self.driver)

            # استخراج داده‌ها
            return self.get_product_data()

        except Exception as e:
            logger.error(f"❌ Error crawling product by URL: {e}")
            return None

    def navigate_to_product(self, asin):
        """رفتن به صفحه محصول با ASIN"""
        try:
            # ساخت URL محصول
            product_url = self.country.get_amazon_product_url(asin)

            logger.info(f"🔄 Navigating to: {product_url}")
            self.driver.get(product_url)

            # منتظر لود شدن صفحه
            self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            time.sleep(3)

            # هندل کردن بلاک
            self.driver_manager.handle_amazon_block(self.driver)

            # شبیه‌سازی رفتار انسانی
            self.driver_manager.simulate_human_behavior(self.driver)

            return True

        except Exception as e:
            logger.error(f"❌ Navigation failed: {e}")
            return False

    def get_product_data(self):
        """استخراج اطلاعات محصول"""
        try:
            if not self._is_product_page_loaded():
                logger.warning("❌ Product page not properly loaded")
                return None

            asin = self._extract_asin()
            if not asin:
                logger.warning("❌ Could not extract ASIN")
                return None

            product_data = {
                'asin': asin,
                'title': self._extract_title(),
                'price': self._extract_price(),
                'currency': self.country.get_currency_code(),
                'brand': self._extract_brand(),
                'seller': self._extract_seller(),
                'seller_id': self._extract_seller_id(),
                'seller_type': self._extract_seller_type(),
                'rating': self._extract_rating(),
                'review_count': self._extract_review_count(),
                'image_url': self._extract_image_url(),
                'category': self._extract_category(),
                'availability': self._extract_availability(),
                'domain': self.country.amazon_domain,
                'description': self._extract_description(),
                'features': self._extract_features(),
                'specifications': self._extract_specifications(),
                'shipping_info': self._extract_shipping_info(),
                'condition': self._extract_condition(),
            }

            logger.info(f"✅ Successfully extracted data for ASIN: {asin}")
            return product_data

        except Exception as e:
            logger.error(f"❌ Error extracting product data: {e}")
            return None

    def _is_product_page_loaded(self):
        """چک کردن آیا صفحه محصول درست لود شده"""
        try:
            indicators = ['#dp', '#productTitle', '#landingImage']
            for indicator in indicators:
                try:
                    self.driver.find_element(By.CSS_SELECTOR, indicator)
                    return True
                except:
                    continue
            return False
        except Exception as e:
            logger.error(f"❌ Error checking page load: {e}")
            return False

    def _extract_asin(self):
        """استخراج ASIN از صفحه"""
        try:
            # از URL
            current_url = self.driver.current_url
            asin_from_url = self.driver_manager.extract_asin_from_url(current_url)
            if asin_from_url:
                return asin_from_url

            # از data attributes
            asin_selectors = ['[data-asin]', '[data-product-asin]', '#ASIN']
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

    def _extract_title(self):
        """استخراج عنوان"""
        selectors = ['#productTitle', '#title', 'h1.a-size-large']
        for selector in selectors:
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

    def _extract_brand(self):
        """استخراج برند"""
        try:
            element = self.driver.find_element(By.ID, "bylineInfo")
            brand_text = element.text.strip()
            clean_brand = brand_text.replace('Visit the', '').replace('Store', '').replace('Brand:', '').strip()
            if clean_brand and len(clean_brand) > 1:
                return clean_brand
        except:
            pass
        return ""

    def _extract_seller(self):
        """استخراج فروشنده"""
        try:
            element = self.driver.find_element(By.ID, "merchant-info")
            seller_text = element.text.strip()

            if 'Ships from and sold by' in seller_text:
                return seller_text.replace('Ships from and sold by', '').split('.')[0].strip()
            elif 'Sold by' in seller_text:
                return seller_text.replace('Sold by', '').split('.')[0].strip()
            elif 'Amazon' in seller_text:
                return 'Amazon'
            else:
                return seller_text.strip()

        except:
            return "Amazon"

    def _extract_seller_id(self):
        """استخراج ID فروشنده"""
        try:
            seller_link = self.driver.find_element(By.CSS_SELECTOR, '[data-csa-c-seller-id]')
            return seller_link.get_attribute('data-csa-c-seller-id')
        except:
            return ""

    def _extract_seller_type(self):
        """استخراج نوع فروشنده"""
        try:
            seller_text = self._extract_seller().lower()

            if 'amazon' in seller_text:
                return 'Amazon'
            elif any(keyword in seller_text for keyword in ['sold by', 'shipped by', 'fulfilled']):
                return 'Third-Party'
            else:
                return 'Third-Party'

        except Exception as e:
            logger.debug(f"Error extracting seller type: {e}")
            return 'Third-Party'

    def _extract_rating(self):
        """استخراج امتیاز"""
        try:
            element = self.driver.find_element(
                By.CSS_SELECTOR,
                '[data-hook="average-star-rating"] .a-icon-alt'
            )
            rating_text = element.text
            rating_match = re.search(r'(\d+\.?\d*) out of 5', rating_text)
            if rating_match:
                return float(rating_match.group(1))
        except:
            pass
        return None

    def _extract_review_count(self):
        """استخراج تعداد نظرات"""
        try:
            element = self.driver.find_element(By.ID, "acrCustomerReviewText")
            review_text = element.text.replace(',', '')
            review_match = re.search(r'([\d,]+)', review_text.replace(',', ''))
            if review_match:
                return int(review_match.group(1))
        except:
            pass
        return 0

    def _extract_image_url(self):
        """استخراج URL تصویر"""
        selectors = ['#landingImage', '#imgBlkFront', '.a-dynamic-image']
        for selector in selectors:
            try:
                element = self.driver.find_element(By.CSS_SELECTOR, selector)
                image_url = element.get_attribute('src') or element.get_attribute('data-old-hires')
                if image_url and 'http' in image_url:
                    return image_url
            except:
                continue
        return ""

    def _extract_category(self):
        """استخراج دسته‌بندی"""
        try:
            elements = self.driver.find_elements(
                By.CSS_SELECTOR,
                '#wayfinding-breadcrumbs_container a'
            )
            categories = [el.text for el in elements if el.text not in ['Home', '›']]
            return ' > '.join(categories) if categories else ""
        except:
            return ""

    def _extract_availability(self):
        """استخراج موجودی"""
        try:
            element = self.driver.find_element(By.ID, "availability")
            availability_text = element.text.lower()
            return 'in stock' in availability_text or 'available' in availability_text
        except:
            return True

    def _extract_description(self):
        """استخراج توضیحات"""
        try:
            desc_selectors = ['#productDescription', '.product-description', '#aplus']
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
        """استخراج ویژگی‌ها"""
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
        """استخراج مشخصات فنی"""
        try:
            specs = {}
            spec_selectors = ['.prodDetTable tr', '.product-specification-table tr']

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
            return specs
        except:
            return {}

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
            condition_selectors = ['#condition', '.a-section.condition']
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

            return 'NEW'
        except:
            return 'NEW'