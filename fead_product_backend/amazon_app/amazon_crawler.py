# amazon_app/amazon_crawler.py
import logging
import uuid
import time
import random
from urllib.parse import urlparse, parse_qs

from django.utils import timezone
from django.db import transaction
from .amazon_driver_manager import AmazonDriverManager  # 🔥 تغییر اینجا
from .geo_manager import AmazonGeoManager
from .amazon_parser import AmazonProductParser
from contract_manager.models import Country
from .models import AmazonProduct, AmazonProductPrice, AmazonCrawlSession

logger = logging.getLogger(__name__)


class AmazonCrawlerService:
    def __init__(self):
        self.driver_manager = AmazonDriverManager()  # 🔥 تغییر اینجا
        self.geo_manager = AmazonGeoManager(self.driver_manager)

    def crawl_product_by_url(self, product_url):
        """کراول کردن محصول با URL"""
        try:
            logger.info(f"🎯 STARTING CRAWL FOR URL: {product_url}")

            # استخراج کشور از URL
            country_code = self.extract_country_from_url(product_url)
            logger.info(f"📍 COUNTRY DETECTED: {country_code}")

            # دریافت کشور از دیتابیس
            try:
                country = Country.objects.get(code=country_code, is_active=True, is_available_for_crawling=True)
                logger.info(f"✅ COUNTRY FOUND IN DB: {country.name}")
            except Country.DoesNotExist:
                logger.error(f"❌ Country not available: {country_code}")
                return None

            # دریافت درایور مخصوص کشور - 🔥 حالا این متد وجود دارد
            driver = self.driver_manager.get_amazon_driver(country_code)
            logger.info(f"🚗 Amazon driver obtained for: {country_code}")

            # تنظیم موقعیت
            logger.info(f"🌍 CONFIGURING AMAZON LOCATION FOR {country.name}")
            self.geo_manager.configure_location(driver, country)

            # ایجاد پارسر
            parser = AmazonProductParser(self.driver_manager, driver, country)

            # کراول کردن
            product_data = parser.crawl_product_by_url(product_url)

            if product_data:
                # ذخیره در دیتابیس
                saved_data = self._save_product_data(product_data, country)
                logger.info(f"✅ Successfully crawled product from URL: {product_url}")
                return saved_data

            return None

        except Exception as e:
            logger.error(f"❌ Error crawling product by URL: {e}")
            return None

    def extract_country_from_url(self, url):
        """استخراج کشور از URL"""
        try:
            from urllib.parse import urlparse

            domain = urlparse(url).netloc.lower()

            country_map = {
                'amazon.com': 'US',
                'amazon.co.uk': 'UK',
                'amazon.de': 'DE',
                'amazon.fr': 'FR',
                'amazon.it': 'IT',
                'amazon.es': 'ES',
                'amazon.ca': 'CA',
                'amazon.co.jp': 'JP',
                'amazon.com.au': 'AU',
            }

            for domain_part, country_code in country_map.items():
                if domain_part in domain:
                    return country_code
            return 'US'
        except:
            return 'US'

    def _save_product_data(self, product_data, country):
        """ذخیره داده‌های محصول"""
        try:
            with transaction.atomic():
                # ایجاد یا آپدیت محصول
                product, created = AmazonProduct.objects.update_or_create(
                    asin=product_data['asin'],
                    country_code=country.code,
                    defaults={
                        'title': product_data.get('title', ''),
                        'description': product_data.get('description', ''),
                        'brand': product_data.get('brand', ''),
                        'category': product_data.get('category', ''),
                        'image_url': product_data.get('image_url', ''),
                        'product_url': country.get_amazon_product_url(product_data['asin']),
                        'condition': product_data.get('condition', 'NEW'),
                        'features': product_data.get('features', []),
                        'specifications': product_data.get('specifications', {}),
                        'rating': product_data.get('rating'),
                        'review_count': product_data.get('review_count', 0),
                        'domain': country.amazon_domain,
                        'seller': product_data.get('seller', ''),
                        'seller_info': {
                            'last_crawled': timezone.now().isoformat(),
                            'seller_id': product_data.get('seller_id', ''),
                            'seller_type': product_data.get('seller_type', '')
                        },
                        'last_crawled': timezone.now(),
                        'is_active': True
                    }
                )

                # ذخیره قیمت
                if product_data.get('price'):
                    AmazonProductPrice.objects.create(
                        product=product,
                        price=product_data['price'],
                        currency=country.get_currency_code(),
                        country_code=country.code,
                        seller=product_data.get('seller', ''),
                        seller_type=product_data.get('seller_type', 'Third-Party'),
                        availability=product_data.get('availability', True),
                        stock_status='In Stock' if product_data.get('availability', True) else 'Out of Stock',
                        shipping_info=product_data.get('shipping_info', ''),
                        crawl_source='url_crawler',
                        crawl_timestamp=timezone.now(),
                    )

                return product_data

        except Exception as e:
            logger.error(f"❌ Error saving product data: {e}")
            return None

    # بقیه متدها...
    def crawl_products(self, asins, country_code='US', driver_name="amazon_crawler", session_id=None):
        """Crawl کردن چندین محصول"""
        if not session_id:
            session_id = str(uuid.uuid4())

        try:
            country = Country.objects.get(code=country_code, is_active=True, is_available_for_crawling=True)
        except Country.DoesNotExist:
            logger.error(f"❌ Country not available: {country_code}")
            return {'error': f'Country {country_code} not available'}

        # ایجاد session
        crawl_session = AmazonCrawlSession.objects.create(
            session_id=session_id,
            driver_name=driver_name,
            country_code=country_code,
            total_products=len(asins),
            status='RUNNING'
        )

        results = {
            'session_id': session_id,
            'country': country_code,
            'successful': [],
            'failed': [],
            'total': len(asins)
        }

        for i, asin in enumerate(asins):
            try:
                logger.info(f"🔄 Processing ASIN {i + 1}/{len(asins)}: {asin}")

                # تأخیر بین درخواست‌ها
                if i > 0:
                    delay = random.uniform(10, 25)
                    logger.info(f"⏳ Waiting {delay:.1f} seconds...")
                    time.sleep(delay)

                # دریافت درایور مخصوص کشور
                driver = self.driver_manager.get_amazon_driver(country_code)

                # تنظیم موقعیت
                self.geo_manager.configure_location(driver, country)

                # ایجاد پارسر
                parser = AmazonProductParser(self.driver_manager, driver, country)

                # crawl محصول
                product_data = parser.navigate_to_product(asin)
                if product_data:
                    product_data = parser.get_product_data()

                if product_data:
                    # ذخیره در دیتابیس
                    self._save_product_data(product_data, country)
                    results['successful'].append(asin)
                    crawl_session.successful_crawls += 1
                    logger.info(f"✅ Successfully crawled: {asin}")
                else:
                    results['failed'].append(asin)
                    crawl_session.failed_crawls += 1
                    logger.warning(f"❌ Failed to crawl: {asin}")

                crawl_session.asins_crawled.append(asin)
                crawl_session.save()

            except Exception as e:
                logger.error(f"💥 Unexpected error crawling {asin}: {e}")
                results['failed'].append(asin)
                crawl_session.failed_crawls += 1
                crawl_session.save()

        # آپدیت وضعیت نهایی
        if crawl_session.failed_crawls == 0:
            crawl_session.status = 'COMPLETED'
        elif crawl_session.successful_crawls > 0:
            crawl_session.status = 'PARTIAL'
        else:
            crawl_session.status = 'FAILED'

        crawl_session.completed_at = timezone.now()
        crawl_session.save()

        logger.info(
            f"🎉 Crawl session completed: {crawl_session.successful_crawls} successful, {crawl_session.failed_crawls} failed")
        return results

    def verify_product_match(self, product_url, expected_asin):
        """تأیید تطابق URL با محصول - بدون لود صفحه"""
        try:
            # استخراج ASIN و seller از URL
            asin_from_url = self.driver_manager.extract_asin_from_url(product_url)
            seller_from_url = self._extract_seller_from_url(product_url)

            # بررسی تطابق ASIN
            asin_match = asin_from_url == expected_asin.upper()

            if not asin_match:
                return {
                    'valid': False,
                    'error': 'ASIN mismatch',
                    'asin_match': False,
                    'seller_match': False,
                    'details': {
                        'asin_from_url': asin_from_url,
                        'expected_asin': expected_asin.upper()
                    }
                }

            # پیدا کردن محصول در دیتابیس
            try:
                product = AmazonProduct.objects.get(asin=expected_asin.upper())
                seller_from_db = product.seller

                # بررسی تطابق seller
                seller_match = self._check_seller_match(seller_from_url, seller_from_db) if seller_from_url else True

                return {
                    'valid': True,
                    'url': product_url,
                    'asin_match': asin_match,
                    'seller_match': seller_match,
                    'details': {
                        'asin_from_url': asin_from_url,
                        'expected_asin': expected_asin.upper(),
                        'seller_from_url': seller_from_url,
                        'seller_from_db': seller_from_db
                    }
                }

            except AmazonProduct.DoesNotExist:
                return {
                    'valid': False,
                    'error': 'Product not found in database',
                    'asin_match': asin_match,
                    'seller_match': False,
                    'details': {
                        'asin_from_url': asin_from_url,
                        'expected_asin': expected_asin.upper(),
                        'seller_from_url': seller_from_url
                    }
                }

        except Exception as e:
            logger.error(f"❌ Error verifying product match: {e}")
            return {
                'valid': False,
                'error': str(e)
            }

    def _extract_seller_from_url(self, url):
        """استخراج seller از URL (پارامتر m)"""
        try:
            parsed_url = urlparse(url)
            query_params = parse_qs(parsed_url.query)

            if 'm' in query_params:
                return query_params['m'][0]
            return ""
        except:
            return ""

    def _check_seller_match(self, seller_from_url, seller_from_db):
        """بررسی تطابق seller"""
        if not seller_from_url or not seller_from_db:
            return True  # اگر یکی خالی باشه، تطابق رو در نظر بگیر

        # نرمال‌سازی برای مقایسه
        url_seller = seller_from_url.lower().replace(' ', '').replace('-', '').replace('_', '')
        db_seller = seller_from_db.lower().replace(' ', '').replace('-', '').replace('_', '')

        return url_seller in db_seller or db_seller in url_seller or url_seller == db_seller

    def get_product_history(self, asin, days=30):
        """دریافت تاریخچه قیمت محصول"""
        from .models import AmazonProductPrice

        cutoff_date = timezone.now() - timezone.timedelta(days=days)

        prices = AmazonProductPrice.objects.filter(
            product__asin=asin,
            crawl_timestamp__gte=cutoff_date
        ).order_by('crawl_timestamp')

        return {
            'asin': asin,
            'price_history': [
                {
                    'price': float(price.price),
                    'currency': price.currency,
                    'timestamp': price.crawl_timestamp.isoformat(),
                    'seller': price.seller,
                    'availability': price.availability
                }
                for price in prices
            ]
        }

    def get_crawl_statistics(self, days=7):
        """آمار crawlهای انجام شده"""
        from .models import AmazonCrawlSession

        cutoff_date = timezone.now() - timezone.timedelta(days=days)

        stats = {
            'total_crawls': AmazonCrawlSession.objects.filter(started_at__gte=cutoff_date).count(),
            'successful_crawls': AmazonCrawlSession.objects.filter(status='COMPLETED',
                                                                   started_at__gte=cutoff_date).count(),
            'failed_crawls': AmazonCrawlSession.objects.filter(status='FAILED', started_at__gte=cutoff_date).count(),
            'total_products_crawled': 0,
            'recent_sessions': []
        }

        recent_sessions = AmazonCrawlSession.objects.filter(
            started_at__gte=cutoff_date
        ).order_by('-started_at')[:10]

        for session in recent_sessions:
            stats['total_products_crawled'] += session.total_products
            stats['recent_sessions'].append({
                'session_id': session.session_id,
                'status': session.status,
                'total_products': session.total_products,
                'successful': session.successful_crawls,
                'failed': session.failed_crawls,
                'started_at': session.started_at.isoformat()
            })

        return stats