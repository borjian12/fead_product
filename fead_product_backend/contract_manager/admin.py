# contract_manager/admin.py
from django.contrib import admin
from .models import Currency, ActionType, Seller, ContractTemplate, Product, ProductContract, ProductTelegramMessage, \
    Country, CountryChannelConfig


@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'amazon_domain', 'default_currency', 'is_active', 'display_order']
    list_filter = ['is_active', 'is_available_for_products']
    search_fields = ['code', 'name', 'native_name']
    readonly_fields = ['created_at', 'updated_at']
    list_editable = ['display_order', 'is_active']

@admin.register(CountryChannelConfig)
class CountryChannelConfigAdmin(admin.ModelAdmin):
    list_display = ['country', 'channel', 'is_primary', 'priority', 'auto_send_new_products', 'is_active']
    list_filter = ['is_primary', 'auto_send_new_products', 'is_active', 'country']
    search_fields = ['country__name', 'channel__name']
    list_editable = ['is_primary', 'priority', 'auto_send_new_products', 'is_active']

@admin.register(Currency)
class CurrencyAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'exchange_rate_to_cny', 'is_active']
    list_filter = ['is_active']
    search_fields = ['code', 'name']


@admin.register(ActionType)
class ActionTypeAdmin(admin.ModelAdmin):
    list_display = ['get_name_display', 'description', 'is_active']
    list_filter = ['is_active']


@admin.register(Seller)
class SellerAdmin(admin.ModelAdmin):
    list_display = ['company_name', 'seller_type', 'user', 'is_verified', 'created_at']
    list_filter = ['seller_type', 'is_verified', 'created_at']
    search_fields = ['company_name', 'user__username']


@admin.register(ContractTemplate)
class ContractTemplateAdmin(admin.ModelAdmin):
    list_display = ['seller', 'action_type', 'refund_percentage', 'commission_amount', 'is_active']
    list_filter = ['seller', 'action_type', 'is_active']
    search_fields = ['seller__company_name']


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['asin', 'title', 'country', 'owner', 'is_active', 'is_stopped', 'created_at']
    list_filter = ['country', 'is_active', 'is_stopped', 'created_at']
    search_fields = ['asin', 'title', 'description']
    readonly_fields = ['created_at', 'updated_at']
    actions = ['send_to_telegram_action', 'send_to_all_channels_action', 'refresh_amazon_data_action']

    def send_to_all_channels_action(self, request, queryset):
        from .services import ProductMessageService
        message_service = ProductMessageService()

        for product in queryset:
            results = message_service.send_product_to_all_country_channels(product)
            for result in results:
                if result['success']:
                    self.message_user(request, f"Product {product.asin} sent to {result['channel']}")
                else:
                    self.message_user(request,
                                      f"Failed to send {product.asin} to {result['channel']}: {result['result']}",
                                      level='error')
    def refresh_amazon_data_action(self, request, queryset):
        """بروزرسانی داده‌های آمازون برای محصولات انتخاب شده"""
        from .services import ProductCrawlerService
        crawler_service = ProductCrawlerService()

        for product in queryset:
            success, message = crawler_service.refresh_product_data(product)
            if success:
                self.message_user(request, f"Product {product.asin} refreshed successfully")
            else:
                self.message_user(request, f"Failed to refresh {product.asin}: {message}", level='error')

    send_to_all_channels_action.short_description = "Send to all country channels"
    refresh_amazon_data_action.short_description = "Refresh Amazon data for selected products"


@admin.register(ProductContract)
class ProductContractAdmin(admin.ModelAdmin):
    list_display = ['product', 'contract_template', 'get_effective_refund_percentage', 'is_active']
    list_filter = ['is_active', 'contract_template__action_type']
    search_fields = ['product__title', 'product__asin']


@admin.register(ProductTelegramMessage)
class ProductTelegramMessageAdmin(admin.ModelAdmin):
    list_display = ['product', 'telegram_message', 'sent_at']
    readonly_fields = ['sent_at']