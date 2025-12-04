from typing import List, Tuple, Optional, Dict
from django.utils import timezone
from django.db.models import Max, Q
from telegram_manager.services import TelegramBotService
from telegram_manager.models import TelegramMessage, TelegramChannel
from .models import Product, ProductContract, CountryChannelConfig, Country, ProductChannel
from amazon_app.amazon_crawler import AmazonCrawlerService
from amazon_app.models import AmazonProduct
from auth_app.models import SellerProfile
import json


class ProductCrawlerService:
    def __init__(self):
        self.amazon_crawler = AmazonCrawlerService()

    def crawl_amazon_product(self, asin: str, country_code: str = "US") -> Tuple[Optional[AmazonProduct], str]:
        """کراول کردن محصول از آمازون با تنظیمات کشور خاص"""
        try:
            # ۱. پیدا کردن کشور
            country = Country.objects.get(code=country_code, is_active=True)

            # ۲. چک کردن وجود محصول در دیتابیس
            try:
                amazon_product = AmazonProduct.objects.get(asin=asin, country=country)
                return amazon_product, "Product already exists in database"
            except AmazonProduct.DoesNotExist:
                pass

            # ۳. کراول کردن از آمازون با تنظیمات کشور
            print(f"🕷️ Crawling Amazon product: {asin} from {country.name}")

            # استفاده از کراولر جدید با پشتیبانی کشور
            crawled_data = self.amazon_crawler.crawl_single_product(
                product_identifier=asin,
                country_code=country_code
            )

            if not crawled_data:
                return None, f"Failed to crawl product from Amazon {country.amazon_domain}"

            # ۴. ذخیره در AmazonProduct با اطلاعات کشور
            amazon_product = AmazonProduct.objects.create(
                asin=crawled_data.get('asin', asin),
                title=crawled_data.get('title', ''),
                price=crawled_data.get('price'),
                currency=crawled_data.get('currency', 'USD'),
                rating=crawled_data.get('rating'),
                review_count=crawled_data.get('review_count', 0),
                brand=crawled_data.get('brand', ''),
                image_url=crawled_data.get('image_url', ''),
                availability=crawled_data.get('availability', True),
                description=crawled_data.get('description', ''),
                features=crawled_data.get('features', []),
                specifications=crawled_data.get('specifications', {}),
                country=country,
                domain=country.amazon_domain,
                geo_location=crawled_data.get('geo_location', {})
            )

            return amazon_product, f"Product crawled successfully from {country.amazon_domain}"

        except Country.DoesNotExist:
            return None, f"Country {country_code} not found or inactive"
        except Exception as e:
            return None, f"Error crawling product: {str(e)}"

    def crawl_and_create_product(self, asin: str, country_code: str, owner: SellerProfile, **product_data) -> Tuple[
        Optional[Product], str]:
        """کراول کردن محصول و ایجاد رکورد کامل در Contract Manager با پشتیبانی کشور"""
        try:
            # ۱. پیدا کردن کشور
            country = Country.objects.get(code=country_code, is_active=True)

            # ۲. کراول کردن داده‌های آمازون
            amazon_product, message = self.crawl_amazon_product(asin, country_code)
            if not amazon_product:
                return None, message

            # ۳. ایجاد محصول در Contract Manager
            product = Product.objects.create(
                asin=asin,
                country=country,
                owner=owner,
                amazon_product=amazon_product,
                title=product_data.get('title') or amazon_product.title,
                description=product_data.get('description') or amazon_product.description,
                product_url=country.get_amazon_product_url(asin),
                daily_max_quantity=product_data.get('daily_max_quantity', 10),
                total_max_quantity=product_data.get('total_max_quantity', 100),
                search_guide=product_data.get('search_guide', ''),
                variant_asins=product_data.get('variant_asins', '')
            )

            return product, f"Product created successfully for {country.name}"

        except Country.DoesNotExist:
            return None, f"Country {country_code} not found"
        except Exception as e:
            return None, f"Error creating product: {str(e)}"

    def refresh_product_data(self, product: Product) -> Tuple[bool, str]:
        """بروزرسانی داده‌های محصول از آمازون با تنظیمات کشور"""
        try:
            print(f"🔄 Refreshing Amazon data for product: {product.asin} from {product.country.name}")

            # کراول کردن داده‌های جدید با کشور محصول
            amazon_product, message = self.crawl_amazon_product(
                product.asin,
                product.country.code
            )

            if amazon_product:
                # آپدیت محصول
                product.amazon_product = amazon_product
                product.title = amazon_product.title or product.title
                product.save()

                return True, f"Product data refreshed successfully from {product.country.amazon_domain}"
            else:
                return False, message

        except Exception as e:
            return False, f"Error refreshing product: {str(e)}"

    def crawl_by_url(self, url: str, owner: SellerProfile, **product_data) -> Tuple[Optional[Product], str]:
        """کراول کردن محصول با URL و ایجاد در Contract Manager"""
        try:
            # استفاده از سرویس کراولینگ آمازون
            crawled_data = self.amazon_crawler.crawl_product_by_url(url)

            if not crawled_data:
                return None, "Failed to crawl product from URL"

            asin = crawled_data.get('asin')
            if not asin:
                return None, "Could not extract ASIN from URL"

            # تشخیص کشور از دامنه
            country_code = self._detect_country_from_url(url)

            # کراول و ایجاد محصول
            return self.crawl_and_create_product(
                asin=asin,
                country_code=country_code,
                owner=owner,
                **product_data
            )

        except Exception as e:
            return None, f"Error crawling product by URL: {str(e)}"

    def _detect_country_from_url(self, url: str) -> str:
        """تشخیص کشور از URL محصول آمازون"""
        country_map = {
            'amazon.com': 'US',
            'amazon.co.uk': 'UK',
            'amazon.de': 'DE',
            'amazon.fr': 'FR',
            'amazon.it': 'IT',
            'amazon.es': 'ES',
            'amazon.ae': 'AE',
            'amazon.sa': 'SA',
            'amazon.com.tr': 'TR',
            'amazon.cn': 'CN',
            'amazon.co.jp': 'JP',
            'amazon.in': 'IN',
            'amazon.com.au': 'AU',
            'amazon.ca': 'CA',
            'amazon.com.br': 'BR',
        }

        for domain, code in country_map.items():
            if domain in url:
                return code
        return 'US'

    def crawl_multiple_products(self, products_data: List[dict]) -> dict:
        """کراول کردن چندین محصول با کشورهای مختلف"""
        results = {
            'successful': [],
            'failed': []
        }

        for product_data in products_data:
            asin = product_data.get('asin')
            country_code = product_data.get('country_code', 'US')
            owner = product_data.get('owner')
            url = product_data.get('url')

            try:
                if url:
                    product, message = self.crawl_by_url(url, owner, **product_data)
                else:
                    product, message = self.crawl_and_create_product(
                        asin=asin,
                        country_code=country_code,
                        owner=owner,
                        **product_data
                    )

                if product:
                    results['successful'].append({
                        'asin': asin,
                        'country': country_code,
                        'product_id': str(product.id),
                        'message': message
                    })
                else:
                    results['failed'].append({
                        'asin': asin,
                        'country': country_code,
                        'error': message
                    })

            except Exception as e:
                results['failed'].append({
                    'asin': asin,
                    'country': country_code,
                    'error': str(e)
                })

        return results


class ProductMessageService:
    def __init__(self):
        self.telegram_service = TelegramBotService()

    def create_product_message_text(self, product: Product, channel_config=None) -> str:
        """ایجاد متن پیام برای محصول با اطلاعات کشور"""
        # استفاده از قالب سفارشی اگر وجود دارد
        if channel_config and channel_config.message_template:
            return self._create_custom_template_message(product, channel_config.message_template)

        # قالب پیش‌فرض با اطلاعات کشور
        return self._create_default_message(product)

    def _create_default_message(self, product: Product) -> str:
        """ایجاد پیام پیش‌فرض با اطلاعات کشور"""
        best_refund = self._calculate_best_refund(product)
        final_price = self._calculate_final_price(product, best_refund)

        message_parts = []

        # هدر با پرچم کشور و دامنه آمازون
        flag_emoji = self._get_country_flag_emoji(product.country.code)
        message_parts.append(f"{flag_emoji} **{product.title}**")
        message_parts.append(f"`{product.country.amazon_domain}`")
        message_parts.append("")

        # اطلاعات کشور
        message_parts.append(f"🌍 **Country:** {product.country.name} ({product.country.code})")

        # قیمت‌ها با ارز مناسب
        if product.amazon_product and product.amazon_product.price:
            original_price = product.amazon_product.price
            currency_symbol = self._get_currency_symbol(product.amazon_product.currency)

            message_parts.append(f"💰 **Price:** {currency_symbol}{original_price:.2f}")

            if best_refund > 0 and final_price:
                message_parts.append(f"🎁 **After Refund:** {currency_symbol}{final_price:.2f}")
                message_parts.append(f"📉 **Refund:** {best_refund}%")

        # وضعیت موجودی
        availability = "✅ In Stock" if product.amazon_product.availability else "❌ Out of Stock"
        message_parts.append(f"📦 **Availability:** {availability}")

        # امتیاز و نظرات
        if product.amazon_product.rating:
            message_parts.append(
                f"⭐ **Rating:** {product.amazon_product.rating}/5 ({product.amazon_product.review_count} reviews)")

        # اقدامات موجود
        available_actions = self._get_available_actions(product)
        if available_actions:
            message_parts.append("")
            message_parts.append("✅ **Available Actions:**")
            for action in available_actions:
                message_parts.append(f"• {action}")

        # راهنمای سرچ
        if product.search_guide:
            message_parts.append("")
            message_parts.append("🔍 **Search Guide:**")
            message_parts.append(product.search_guide)

        # لینک محصول
        message_parts.append("")
        message_parts.append(f"🔗 [View on Amazon]({product.get_amazon_url()})")

        return "\n".join(message_parts)

    def _create_custom_template_message(self, product: Product, template: str) -> str:
        """ایجاد پیام با قالب سفارشی"""
        context = self._get_message_context(product)

        # جایگزینی متغیرها در قالب
        message = template
        for key, value in context.items():
            placeholder = f"{{{{{key}}}}}"
            message = message.replace(placeholder, str(value))

        return message

    def _get_message_context(self, product: Product) -> dict:
        """دریافت context برای قالب‌بندی با اطلاعات کشور"""
        best_refund = self._calculate_best_refund(product)
        final_price = self._calculate_final_price(product, best_refund)

        return {
            'product_title': product.title,
            'product_asin': product.asin,
            'country_name': product.country.name,
            'country_code': product.country.code,
            'amazon_domain': product.country.amazon_domain,
            'original_price': product.amazon_product.price if product.amazon_product else 'N/A',
            'currency': product.amazon_product.currency if product.amazon_product else 'USD',
            'final_price': final_price or 'N/A',
            'refund_percentage': best_refund,
            'availability': "In Stock" if product.amazon_product.availability else "Out of Stock",
            'rating': product.amazon_product.rating if product.amazon_product else 'N/A',
            'review_count': product.amazon_product.review_count if product.amazon_product else 0,
            'available_actions': ', '.join(self._get_available_actions(product)),
            'search_guide': product.search_guide or 'No search guide provided',
            'amazon_url': product.get_amazon_url(),
            'product_description': product.description or 'No description available',
            'flag_emoji': self._get_country_flag_emoji(product.country.code),
            'currency_symbol': self._get_currency_symbol(
                product.amazon_product.currency if product.amazon_product else 'USD'),
        }

    def prepare_product_for_channels(self, product: Product, channel_ids: List[str] = None) -> List[ProductChannel]:
        """آماده‌سازی محصول برای ارسال به کانال‌ها"""
        prepared_messages = []

        # اگر channel_ids مشخص شده، فقط آن کانال‌ها
        if channel_ids:
            channels = TelegramChannel.objects.filter(
                id__in=channel_ids,
                is_active=True
            )
        else:
            # همه کانال‌های مرتبط با کشور
            channels = product.get_related_channels()

        for channel in channels:
            # بررسی تنظیمات کانال
            try:
                channel_config = CountryChannelConfig.objects.get(
                    country=product.country,
                    channel=channel,
                    is_active=True
                )
                if not channel_config.auto_send_new_products:
                    continue
            except CountryChannelConfig.DoesNotExist:
                pass  # ارسال شود

            # ایجاد متن پیام
            message_text = self.create_product_message_text(product)

            # ایجاد ProductChannel
            product_channel = product.create_or_update_telegram_message(
                channel=channel,
                message_text=message_text,
                images=self._get_product_images(product)
            )

            if product_channel:
                prepared_messages.append(product_channel)

        return prepared_messages

    def send_product_to_channels(self, product: Product, channel_ids: List[str] = None) -> Dict:
        """ارسال محصول به کانال‌های تلگرام"""
        results = {
            'successful': [],
            'failed': [],
            'total': 0
        }

        # آماده‌سازی پیام‌ها
        product_channels = self.prepare_product_for_channels(product, channel_ids)
        results['total'] = len(product_channels)

        for product_channel in product_channels:
            try:
                # ارسال به تلگرام
                success, telegram_message_id, error = self.telegram_service.send_message(
                    product_channel.channel.channel_id,
                    product_channel.telegram_message_text,
                    product_channel.telegram_images
                )

                if success:
                    product_channel.mark_as_sent(telegram_message_id)

                    # ذخیره در TelegramMessage برای سازگاری
                    telegram_message = TelegramMessage.objects.create(
                        channel=product_channel.channel,
                        message_text=product_channel.telegram_message_text,
                        images=product_channel.telegram_images,
                        telegram_message_id=telegram_message_id,
                        status='sent',
                        sent_at=timezone.now(),
                        created_by=product.owner.user
                    )

                    results['successful'].append({
                        'channel': product_channel.channel.name,
                        'message_id': telegram_message_id,
                        'product_channel_id': product_channel.id
                    })
                else:
                    product_channel.status = 'failed'
                    product_channel.error_log = error
                    product_channel.save()

                    results['failed'].append({
                        'channel': product_channel.channel.name,
                        'error': error,
                        'product_channel_id': product_channel.id
                    })

            except Exception as e:
                error_msg = f"Unexpected error: {str(e)}"
                product_channel.status = 'failed'
                product_channel.error_log = error_msg
                product_channel.save()

                results['failed'].append({
                    'channel': product_channel.channel.name,
                    'error': error_msg,
                    'product_channel_id': product_channel.id
                })

        return results

    def update_telegram_messages(self, product: Product) -> Dict:
        """بروزرسانی پیام‌های تلگرام ارسال شده برای محصول"""
        results = {
            'updated': [],
            'failed': [],
            'total': 0
        }

        # پیام‌های ارسال شده
        product_channels = ProductChannel.objects.filter(
            product=product,
            status='sent',
            auto_update=True
        )

        results['total'] = product_channels.count()

        for product_channel in product_channels:
            try:
                # ایجاد متن جدید
                new_message_text = self.create_product_message_text(product)

                # ویرایش پیام در تلگرام
                success, error = self.telegram_service.edit_message(
                    product_channel.channel.channel_id,
                    product_channel.telegram_message_id,
                    new_message_text
                )

                if success:
                    product_channel.telegram_message_text = new_message_text
                    product_channel.mark_as_edited()

                    # بروزرسانی TelegramMessage مرتبط
                    try:
                        telegram_message = TelegramMessage.objects.get(
                            telegram_message_id=product_channel.telegram_message_id
                        )
                        telegram_message.message_text = new_message_text
                        telegram_message.status = 'edited'
                        telegram_message.save()
                    except TelegramMessage.DoesNotExist:
                        pass

                    results['updated'].append({
                        'channel': product_channel.channel.name,
                        'message_id': product_channel.telegram_message_id
                    })
                else:
                    results['failed'].append({
                        'channel': product_channel.channel.name,
                        'error': error
                    })

            except Exception as e:
                results['failed'].append({
                    'channel': product_channel.channel.name,
                    'error': str(e)
                })

        return results

    def stop_telegram_messages(self, product: Product) -> Dict:
        """متوقف کردن پیام‌های تلگرام محصول"""
        results = {
            'stopped': [],
            'failed': [],
            'total': 0
        }

        # پیام‌های ارسال شده
        product_channels = ProductChannel.objects.filter(
            product=product,
            status='sent'
        )

        results['total'] = product_channels.count()

        for product_channel in product_channels:
            try:
                # حذف پیام از تلگرام
                success, error = self.telegram_service.delete_message(
                    product_channel.channel.channel_id,
                    product_channel.telegram_message_id
                )

                if success:
                    product_channel.mark_as_stopped()
                    results['stopped'].append({
                        'channel': product_channel.channel.name,
                        'message_id': product_channel.telegram_message_id
                    })
                else:
                    results['failed'].append({
                        'channel': product_channel.channel.name,
                        'error': error
                    })

            except Exception as e:
                results['failed'].append({
                    'channel': product_channel.channel.name,
                    'error': str(e)
                })

        return results

    def delete_telegram_messages(self, product: Product) -> Dict:
        """حذف پیام‌های تلگرام محصول"""
        results = {
            'deleted': [],
            'failed': [],
            'total': 0
        }

        # همه پیام‌های محصول
        product_channels = ProductChannel.objects.filter(product=product)

        results['total'] = product_channels.count()

        for product_channel in product_channels:
            try:
                # حذف از تلگرام اگر ارسال شده
                if product_channel.telegram_message_id:
                    self.telegram_service.delete_message(
                        product_channel.channel.channel_id,
                        product_channel.telegram_message_id
                    )

                # حذف از دیتابیس
                product_channel.mark_as_deleted()
                results['deleted'].append({
                    'channel': product_channel.channel.name,
                    'message_id': product_channel.telegram_message_id
                })

            except Exception as e:
                results['failed'].append({
                    'channel': product_channel.channel.name,
                    'error': str(e)
                })

        return results

    # متدهای کمکی
    def _calculate_best_refund(self, product: Product) -> float:
        """محاسبه بهترین درصد ریفاند"""
        try:
            contracts = ProductContract.objects.filter(
                product=product,
                is_active=True
            )
            if contracts.exists():
                max_refund = contracts.aggregate(
                    max_refund=Max('contract_template__refund_percentage')
                )['max_refund']
                return float(max_refund) if max_refund else 0
            return 0
        except Exception as e:
            print(f"Error calculating best refund: {e}")
            return 0

    def _calculate_final_price(self, product: Product, refund_percentage: float) -> Optional[float]:
        """محاسبه قیمت نهایی پس از ریفاند"""
        try:
            if (product.amazon_product and
                    product.amazon_product.price and
                    refund_percentage > 0):
                original_price = float(product.amazon_product.price)
                refund_amount = original_price * (refund_percentage / 100)
                return round(original_price - refund_amount, 2)
            return None
        except Exception as e:
            print(f"Error calculating final price: {e}")
            return None

    def _get_available_actions(self, product: Product) -> List[str]:
        """لیست اقدامات موجود"""
        try:
            contracts = ProductContract.objects.filter(
                product=product,
                is_active=True
            ).select_related('contract_template__action_type')

            actions = []
            for contract in contracts:
                action_name = contract.contract_template.action_type.get_name_display()
                refund = contract.get_effective_refund_percentage()
                actions.append(f"{action_name} ({refund}% refund)")

            return actions
        except Exception as e:
            print(f"Error getting available actions: {e}")
            return []

    def _get_country_flag_emoji(self, country_code: str) -> str:
        """دریافت ایموجی پرچم کشور"""
        flag_emojis = {
            'US': '🇺🇸', 'UK': '🇬🇧', 'DE': '🇩🇪', 'FR': '🇫🇷', 'IT': '🇮🇹',
            'ES': '🇪🇸', 'IR': '🇮🇷', 'TR': '🇹🇷', 'AE': '🇦🇪', 'SA': '🇸🇦',
            'CN': '🇨🇳', 'JP': '🇯🇵', 'KR': '🇰🇷', 'IN': '🇮🇳', 'BR': '🇧🇷',
            'CA': '🇨🇦', 'AU': '🇦🇺', 'NL': '🇳🇱', 'SE': '🇸🇪'
        }
        return flag_emojis.get(country_code, '🛍️')

    def _get_currency_symbol(self, currency_code: str) -> str:
        """دریافت نماد ارز"""
        symbols = {
            'USD': '$', 'EUR': '€', 'GBP': '£', 'CNY': '¥',
            'JPY': '¥', 'INR': '₹', 'CAD': 'C$', 'AUD': 'A$',
            'AED': 'د.إ', 'SAR': 'ر.س', 'TRY': '₺', 'BRL': 'R$'
        }
        return symbols.get(currency_code, '$')

    def _get_product_images(self, product: Product) -> List[str]:
        """دریافت عکس‌های محصول"""
        try:
            images = []
            if product.amazon_product and product.amazon_product.image_url:
                images.append(product.amazon_product.image_url)
            return images
        except Exception as e:
            print(f"Error getting product images: {e}")
            return []