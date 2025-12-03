# contract_manager/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from .models import Product, Country, ProductChannel
from .services import ProductMessageService, ProductCrawlerService


@login_required
def product_list(request):
    """لیست محصولات"""
    try:
        seller = request.user.seller
        products = Product.objects.filter(owner=seller).select_related(
            'country', 'amazon_product'
        ).order_by('-created_at')

        return render(request, 'contract_manager/product_list.html', {
            'products': products,
            'seller': seller
        })
    except Exception as e:
        messages.error(request, f'Error loading products: {str(e)}')
        return render(request, 'contract_manager/product_list.html', {
            'products': []
        })


@login_required
def create_product(request):
    """صفحه ایجاد محصول جدید"""
    countries = Country.objects.filter(
        is_active=True,
        is_available_for_products=True
    ).order_by('display_order', 'name')

    if request.method == 'POST':
        try:
            seller = request.user.seller

            # دریافت داده‌ها
            asin = request.POST.get('asin')
            url = request.POST.get('url')
            country_code = request.POST.get('country_code')

            if not (asin or url):
                messages.error(request, 'Either ASIN or URL is required')
                return redirect('contract_manager:create_product')

            # استفاده از سرویس کراولر
            crawler_service = ProductCrawlerService()

            if url:
                # ایجاد از URL
                product, message = crawler_service.crawl_by_url(
                    url=url,
                    owner=seller,
                    title=request.POST.get('title'),
                    description=request.POST.get('description'),
                    search_guide=request.POST.get('search_guide'),
                    daily_max_quantity=request.POST.get('daily_max_quantity', 10),
                    total_max_quantity=request.POST.get('total_max_quantity', 100),
                    variant_asins=request.POST.get('variant_asins', '')
                )
            else:
                # ایجاد از ASIN
                product, message = crawler_service.crawl_and_create_product(
                    asin=asin,
                    country_code=country_code,
                    owner=seller,
                    title=request.POST.get('title'),
                    description=request.POST.get('description'),
                    search_guide=request.POST.get('search_guide'),
                    daily_max_quantity=request.POST.get('daily_max_quantity', 10),
                    total_max_quantity=request.POST.get('total_max_quantity', 100),
                    variant_asins=request.POST.get('variant_asins', '')
                )

            if product:
                messages.success(request, f'Product created: {message}')

                # بررسی ارسال خودکار
                auto_send = request.POST.get('auto_send') == 'on'
                if auto_send:
                    return redirect('contract_manager:send_to_telegram', product_id=product.id)
                else:
                    return redirect('contract_manager:product_detail', product_id=product.id)
            else:
                messages.error(request, f'Failed to create product: {message}')

        except Exception as e:
            messages.error(request, f'Error creating product: {str(e)}')

    return render(request, 'contract_manager/create_product.html', {
        'countries': countries
    })


@login_required
def product_detail(request, product_id):
    """صفحه جزییات محصول"""
    try:
        seller = request.user.seller
        product = get_object_or_404(Product, id=product_id, owner=seller)

        # پیام‌های تلگرام
        telegram_messages = ProductChannel.objects.filter(
            product=product
        ).select_related('channel').order_by('-sent_at')

        # کانال‌های موجود برای این کشور
        available_channels = product.get_related_channels()

        return render(request, 'contract_manager/product_detail.html', {
            'product': product,
            'telegram_messages': telegram_messages,
            'available_channels': available_channels,
            'has_channels': available_channels.exists()
        })
    except Exception as e:
        messages.error(request, f'Error loading product: {str(e)}')
        return redirect('contract_manager:product_list')


@login_required
def send_to_telegram(request, product_id):
    """ارسال محصول به تلگرام"""
    try:
        seller = request.user.seller
        product = get_object_or_404(Product, id=product_id, owner=seller)

        # کانال‌های قابل ارسال
        available_channels = product.get_related_channels()

        if not available_channels.exists():
            messages.warning(request, 'No active channels found for this product\'s country')
            return redirect('contract_manager:product_detail', product_id=product_id)

        if request.method == 'POST':
            # دریافت کانال‌های انتخاب شده
            selected_channels = request.POST.getlist('channels')

            if not selected_channels:
                messages.error(request, 'Please select at least one channel')
                return redirect('contract_manager:send_to_telegram', product_id=product_id)

            # ارسال به کانال‌ها
            message_service = ProductMessageService()
            results = message_service.send_product_to_channels(
                product=product,
                channel_ids=selected_channels
            )

            if results['successful']:
                messages.success(request, f'Product sent to {len(results["successful"])} channel(s) successfully')
            else:
                messages.warning(request,
                                 f'Sent to {len(results["successful"])} channels, failed for {len(results["failed"])}')

            return redirect('contract_manager:product_detail', product_id=product_id)

        return render(request, 'contract_manager/send_to_telegram.html', {
            'product': product,
            'available_channels': available_channels
        })

    except Exception as e:
        messages.error(request, f'Error sending to Telegram: {str(e)}')
        return redirect('contract_manager:product_detail', product_id=product_id)


@login_required
def refresh_product_data(request, product_id):
    """بروزرسانی داده‌های محصول از آمازون"""
    try:
        seller = request.user.seller
        product = get_object_or_404(Product, id=product_id, owner=seller)

        crawler_service = ProductCrawlerService()
        success, message = crawler_service.refresh_product_data(product)

        if success:
            messages.success(request, f'Product data refreshed: {message}')

            # بروزرسانی پیام‌های تلگرام اگر درخواست شده
            update_messages = request.GET.get('update_messages') == 'true'
            if update_messages:
                message_service = ProductMessageService()
                update_results = message_service.update_telegram_messages(product)

                if update_results['updated']:
                    messages.success(request, f'Updated {len(update_results["updated"])} Telegram message(s)')
        else:
            messages.error(request, f'Failed to refresh product: {message}')

        return redirect('contract_manager:product_detail', product_id=product_id)

    except Exception as e:
        messages.error(request, f'Error refreshing product: {str(e)}')
        return redirect('contract_manager:product_detail', product_id=product_id)


@login_required
def edit_product(request, product_id):
    """ویرایش محصول"""
    try:
        seller = request.user.seller
        product = get_object_or_404(Product, id=product_id, owner=seller)

        if request.method == 'POST':
            # بروزرسانی فیلدها
            product.title = request.POST.get('title', product.title)
            product.description = request.POST.get('description', product.description)
            product.search_guide = request.POST.get('search_guide', product.search_guide)
            product.daily_max_quantity = int(request.POST.get('daily_max_quantity', product.daily_max_quantity))
            product.total_max_quantity = int(request.POST.get('total_max_quantity', product.total_max_quantity))
            product.variant_asins = request.POST.get('variant_asins', product.variant_asins)
            product.is_active = request.POST.get('is_active') == 'on'

            product.save()

            messages.success(request, 'Product updated successfully')

            # بروزرسانی پیام‌های تلگرام اگر درخواست شده
            update_telegram = request.POST.get('update_telegram') == 'on'
            if update_telegram and product.get_telegram_messages().exists():
                message_service = ProductMessageService()
                update_results = message_service.update_telegram_messages(product)

                if update_results['updated']:
                    messages.success(request, f'Updated {len(update_results["updated"])} Telegram message(s)')

            return redirect('contract_manager:product_detail', product_id=product_id)

        return render(request, 'contract_manager/edit_product.html', {
            'product': product
        })

    except Exception as e:
        messages.error(request, f'Error editing product: {str(e)}')
        return redirect('contract_manager:product_detail', product_id=product_id)