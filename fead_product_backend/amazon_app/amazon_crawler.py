# amazon_app/amazon_crawler.py
import logging
import uuid
import time
import random
from datetime import datetime
from django.utils import timezone
from django.db import transaction
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium_app.driver_manager import SeleniumDriverManager
from .models import AmazonProduct, AmazonProductPrice, AmazonCrawlSession
from .amazon_parser import AmazonPageParser

logger = logging.getLogger(__name__)


class AmazonCrawlerService:
    def __init__(self):
        self.driver_manager = SeleniumDriverManager()

    def get_amazon_driver(self, driver_name="amazon_crawler"):
        """دریافت درایور مخصوص Amazon"""
        profile_data = {
            'headless': False,  # مهم: برای دیدن در VNC
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'window_size': '1920,1080',
        }

        return self.driver_manager.get_or_create_driver(
            driver_name,
            driver_type='CHROME',
            profile_data=profile_data
        )

    def crawl_products(self, asins, driver_name="amazon_crawler", session_id=None):
        """Crawl کردن محصولات"""
        if not session_id:
            session_id = str(uuid.uuid4())

        # ایجاد session
        crawl_session = AmazonCrawlSession.objects.create(
            session_id=session_id,
            driver_name=driver_name,
            total_products=len(asins),
            status='RUNNING'
        )

        results = {
            'session_id': session_id,
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

                # crawl محصول
                product_data = self._crawl_single_product(asin, driver_name)

                if product_data:
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

    def _crawl_single_product(self, asin, driver_name):
        """Crawl کردن یک محصول"""
        try:
            # دریافت درایور
            driver = self.get_amazon_driver(driver_name)

            # ایجاد پارسر
            parser = AmazonPageParser(driver)

            # رفتن به صفحه محصول
            if not parser.navigate_to_product_page(asin):
                return None

            # استخراج داده‌ها
            product_data = parser.get_product_data()
            if not product_data:
                return None

            # ذخیره در دیتابیس
            return self._save_product_data(product_data, driver_name)

        except Exception as e:
            logger.error(f"❌ Error crawling product {asin}: {e}")
            return None

    def _save_product_data(self, product_data, driver_name):
        """ذخیره داده‌های محصول با بررسی تاریخ آخرین crawl"""
        try:
            with transaction.atomic():
                # ایجاد یا آپدیت محصول
                product, created = AmazonProduct.objects.update_or_create(
                    asin=product_data['asin'],
                    defaults={
                        'title': product_data.get('title', ''),
                        'description': product_data.get('description', ''),
                        'brand': product_data.get('brand', ''),
                        'category': product_data.get('category', ''),
                        'image_url': product_data.get('image_url', ''),
                        'product_url': f"https://www.amazon.com/dp/{product_data['asin']}",
                        'condition': product_data.get('condition', 'NEW'),
                        'features': product_data.get('features', []),
                        'specifications': product_data.get('specifications', {}),
                        'rating': product_data.get('rating'),
                        'review_count': product_data.get('review_count', 0),
                        'last_crawled': timezone.now(),
                        'is_active': True
                    }
                )

                # 🔥 بخش جدید: بررسی آیا در 24 ساعت گذشته قیمت ثبت شده
                if product_data.get('price'):
                    # پیدا کردن آخرین قیمت ثبت شده برای این محصول
                    last_price = AmazonProductPrice.objects.filter(
                        product=product,
                        crawl_timestamp__gte=timezone.now() - timezone.timedelta(hours=24)
                    ).order_by('-crawl_timestamp').first()

                    if last_price:
                        # اگر قیمت در 24 ساعت گذشته ثبت شده، فقط لاگ می‌کنیم
                        logger.info(
                            f"💰 Price already exists for ASIN {product_data['asin']} in last 24 hours. Skipping new price record.")
                        logger.info(
                            f"   Last price: {last_price.price} {last_price.currency} at {last_price.crawl_timestamp}")
                        logger.info(f"   Current price: {product_data['price']} {product_data.get('currency', 'USD')}")
                    else:
                        # اگر قیمت در 24 ساعت گذشته ثبت نشده، رکورد جدید ایجاد می‌کنیم
                        AmazonProductPrice.objects.create(
                            product=product,
                            price=product_data['price'],
                            currency=product_data.get('currency', 'USD'),
                            seller=product_data.get('seller', 'Amazon'),
                            seller_type='Amazon' if 'amazon' in product_data.get('seller',
                                                                                 '').lower() else 'Third-Party',
                            availability=product_data.get('availability', True),
                            stock_status='In Stock' if product_data.get('availability', True) else 'Out of Stock',
                            shipping_info=product_data.get('shipping_info', ''),
                            crawl_source=driver_name,
                            crawl_timestamp=timezone.now(),
                            metadata={
                                'session_url': f"https://www.amazon.com/dp/{product_data['asin']}",
                                'price_change': self._calculate_price_change(product, product_data['price'])
                            }
                        )
                        logger.info(
                            f"✅ New price record created for ASIN {product_data['asin']}: {product_data['price']} {product_data.get('currency', 'USD')}")

                return product_data

        except Exception as e:
            logger.error(f"❌ Error saving product data: {e}")
            return None

    def _calculate_price_change(self, product, current_price):
        """محاسبه تغییرات قیمت نسبت به آخرین رکورد"""
        try:
            # پیدا کردن آخرین قیمت قبل از 24 ساعت گذشته
            last_old_price = AmazonProductPrice.objects.filter(
                product=product,
                crawl_timestamp__lt=timezone.now() - timezone.timedelta(hours=24)
            ).order_by('-crawl_timestamp').first()

            if last_old_price:
                price_diff = current_price - last_old_price.price
                price_diff_percent = (price_diff / last_old_price.price) * 100 if last_old_price.price else 0

                return {
                    'previous_price': float(last_old_price.price),
                    'price_difference': float(price_diff),
                    'percentage_change': float(price_diff_percent),
                    'trend': 'up' if price_diff > 0 else 'down' if price_diff < 0 else 'stable'
                }
            return None
        except Exception as e:
            logger.debug(f"Could not calculate price change: {e}")
            return None

    # متدهای کمکی همون قبلی می‌مونن
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