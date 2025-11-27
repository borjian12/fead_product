# contract_manager/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Product, ProductContract
from .services import ProductMessageService


@login_required
def product_list(request):
    """لیست محصولات"""
    products = Product.objects.filter(owner__user=request.user).select_related('amazon_product')
    return render(request, 'contract_manager/product_list.html', {
        'products': products
    })


@login_required
def product_detail(request, product_id):
    """صفحه جزییات محصول"""
    product = get_object_or_404(Product, id=product_id, owner__user=request.user)
    contracts = ProductContract.objects.filter(product=product).select_related('contract_template')
    telegram_messages = product.producttelegrammessage_set.select_related('telegram_message')

    return render(request, 'contract_manager/product_detail.html', {
        'product': product,
        'contracts': contracts,
        'telegram_messages': telegram_messages
    })


@login_required
def send_to_telegram(request, product_id):
    """ارسال محصول به تلگرام"""
    product = get_object_or_404(Product, id=product_id, owner__user=request.user)

    message_service = ProductMessageService()
    success, result = message_service.send_product_to_telegram(product)

    if success:
        messages.success(request, f"Product sent to Telegram! Message ID: {result}")
    else:
        messages.error(request, f"Failed to send product: {result}")

    return redirect('contract_manager:product_detail', product_id=product_id)


@login_required
def refresh_product_data(request, product_id):
    """بروزرسانی داده‌های محصول از آمازون"""
    product = get_object_or_404(Product, id=product_id, owner__user=request.user)

    from .services import ProductCrawlerService
    crawler_service = ProductCrawlerService()

    success, message = crawler_service.refresh_product_data(product)

    if success:
        messages.success(request, f"Product data refreshed successfully: {message}")
    else:
        messages.error(request, f"Failed to refresh product data: {message}")

    return redirect('contract_manager:product_detail', product_id=product_id)