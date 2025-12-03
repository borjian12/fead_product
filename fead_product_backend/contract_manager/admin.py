# contract_manager/admin.py
from django.contrib import admin
from .models import (
    Currency, Country, CountryChannelConfig,
    ActionType, Seller, ContractTemplate,
    Product, ProductContract, ProductChannel,
    ProductUpdateLog
)

@admin.register(Currency)
class CurrencyAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'exchange_rate_to_cny', 'is_active']
    search_fields = ['code', 'name']

@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'amazon_domain', 'is_active']
    list_filter = ['is_active', 'is_available_for_crawling']
    search_fields = ['code', 'name', 'amazon_domain']

@admin.register(Seller)
class SellerAdmin(admin.ModelAdmin):
    list_display = ['user', 'company_name', 'seller_type', 'is_verified']
    search_fields = ['company_name', 'contact_email']
    list_filter = ['seller_type', 'is_verified']

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['asin', 'title', 'country', 'owner', 'is_active', 'is_stopped']
    list_filter = ['country', 'is_active', 'is_stopped']
    search_fields = ['asin', 'title']
    raw_id_fields = ['amazon_product', 'owner']

@admin.register(ProductChannel)
class ProductChannelAdmin(admin.ModelAdmin):
    list_display = ['product', 'channel', 'status', 'sent_at']
    list_filter = ['status', 'sent_at']
    search_fields = ['product__asin', 'channel__name']

# ثبت بقیه مدل‌ها
admin.site.register(CountryChannelConfig)
admin.site.register(ActionType)
admin.site.register(ContractTemplate)
admin.site.register(ProductContract)
admin.site.register(ProductUpdateLog)