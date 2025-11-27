# contract_manager/services.py
from typing import List

from django.utils import timezone
from django.db.models import Max
from telegram_manager.services import TelegramBotService
from telegram_manager.models import TelegramMessage
from .models import Product, ProductContract, CountryChannelConfig, Country
from amazon_app.amazon_crawler import AmazonCrawlerService
from amazon_app.models import AmazonProduct


class ProductCrawlerService:
    def __init__(self):
        self.amazon_crawler = AmazonCrawlerService()

    def crawl_amazon_product(self, asin: str, country_code: str = "US") -> tuple:
        """کراول کردن محصول از آمازون با تنظیمات کشور خاص"""
        try:
            # ۱. پیدا کردن کشور
            country = Country.objects.get(code=country_code, is_active=True)

            # ۲. چک کردن وجود محصول در دیتابیس
            from amazon_app.models import AmazonProduct
            try:
                amazon_product = AmazonProduct.objects.get(asin=asin, country=country)
                return amazon_product, "Product already exists in database"
            except AmazonProduct.DoesNotExist:
                pass

            # ۳. کراول کردن از آمازون با تنظیمات کشور
            print(f"🕷️ Crawling Amazon product: {asin} from {country.name}")

            # استفاده از کراولر جدید با پشتیبانی کشور
            crawled_data = self.amazon_crawler.crawl_product(
                product_identifier=asin,
                country_code=country_code
            )

            if not crawled_data:
                return None, f"Failed to crawl product from Amazon {country.amazon_domain}"

            # ۴. ذخیره در AmazonProduct با اطلاعات کشور
            amazon_product = AmazonProduct.objects.create(
                asin=crawled_data['asin'],
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

            # ۵. ذخیره variantها اگر وجود دارند
            if crawled_data.get('variants'):
                self._save_product_variants(amazon_product, crawled_data['variants'])

            return amazon_product, f"Product crawled successfully from {country.amazon_domain}"

        except Country.DoesNotExist:
            return None, f"Country {country_code} not found or inactive"
        except Exception as e:
            return None, f"Error crawling product: {str(e)}"

    def crawl_and_create_product(self, asin: str, country_code: str, owner, **product_data) -> tuple:
        """کراول کردن محصول و ایجاد رکورد کامل در Contract Manager با پشتیبانی کشور"""
        try:
            from .models import Product

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
            )

            # ۴. استخراج و ذخیره variant ASIN ها
            if amazon_product.variants:
                variant_asins = [v.get('asin') for v in amazon_product.variants if v.get('asin')]
                product.variant_asins = ','.join(variant_asins)
                product.save()

            return product, f"Product created successfully for {country.name}"

        except Country.DoesNotExist:
            return None, f"Country {country_code} not found"
        except Exception as e:
            return None, f"Error creating product: {str(e)}"

    def refresh_product_data(self, product: Product) -> tuple:
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

                # آپدیت variantها
                if amazon_product.variants:
                    variant_asins = [v.get('asin') for v in amazon_product.variants if v.get('asin')]
                    product.variant_asins = ','.join(variant_asins)

                product.save()
                return True, f"Product data refreshed successfully from {product.country.amazon_domain}"
            else:
                return False, message

        except Exception as e:
            return False, f"Error refreshing product: {str(e)}"

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

            try:
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
                        'product_id': product.id,
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
        }

    def send_product_to_telegram(self, product: Product, channel_config=None) -> tuple:
        """ارسال محصول به تلگرام با اطلاعات کشور"""
        try:
            if channel_config:
                channel = channel_config.channel
            else:
                channel = product.get_primary_channel()

            if not channel:
                return False, "No active channel found for product country"

            message_text = self.create_product_message_text(product, channel_config)
            images = self._get_product_images(product)

            print(f"📤 Sending product {product.asin} from {product.country.name} to channel {channel.name}")

            # ارسال پیام
            success, telegram_message_id, error = self.telegram_service.send_message(
                channel.channel_id,
                message_text,
                images
            )

            if success:
                # ذخیره پیام در دیتابیس
                telegram_message = TelegramMessage.objects.create(
                    channel=channel,
                    message_text=message_text,
                    images=images,
                    telegram_message_id=telegram_message_id,
                    status='sent',
                    sent_at=timezone.now(),
                    created_by=product.owner.user
                )

                # ایجاد ارتباط با محصول
                from .models import ProductTelegramMessage
                ProductTelegramMessage.objects.create(
                    product=product,
                    telegram_message=telegram_message
                )

                print(f"✅ Product {product.asin} from {product.country.name} sent successfully to Telegram")
                return True, telegram_message_id
            else:
                print(f"❌ Failed to send product {product.asin}: {error}")
                return False, error

        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            print(f"❌ Error in send_product_to_telegram: {error_msg}")
            return False, error_msg

    # سایر متدهای کمکی...
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
            'JPY': '¥', 'INR': '₹', 'CAD': 'C$', 'AUD': 'A$'
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
