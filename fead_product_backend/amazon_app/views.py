# amazon_app/views.py
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
from .amazon_crawler import AmazonCrawlerService

crawler_service = AmazonCrawlerService()


@csrf_exempt
@require_http_methods(["POST"])
def crawl_products(request):
    """Crawl کردن محصولات جدید"""
    try:
        data = json.loads(request.body)
        asins = data.get('asins', [])
        driver_name = data.get('driver_name', 'amazon_crawler')
        session_id = data.get('session_id')

        if not asins:
            return JsonResponse({'error': 'ASINs list is required'}, status=400)

        # اعتبارسنجی ASINها
        valid_asins = []
        for asin in asins:
            if len(asin) == 10 and asin.isalnum():
                valid_asins.append(asin.upper())

        if not valid_asins:
            return JsonResponse({'error': 'No valid ASINs provided'}, status=400)

        results = crawler_service.crawl_products(valid_asins, driver_name, session_id)

        return JsonResponse({
            'success': True,
            'session_id': results['session_id'],
            'results': {
                'total': results['total'],
                'successful': len(results['successful']),
                'failed': len(results['failed']),
                'failed_asins': results['failed']
            }
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["GET"])
def get_product_info(request, asin):
    """دریافت اطلاعات محصول"""
    try:
        from .models import AmazonProduct

        product = AmazonProduct.objects.get(asin=asin.upper())
        latest_price = product.prices.order_by('-crawl_timestamp').first()

        response_data = {
            'asin': product.asin,
            'title': product.title,
            'brand': product.brand,
            'category': product.category,
            'rating': float(product.rating) if product.rating else None,
            'review_count': product.review_count,
            'image_url': product.image_url,
            'condition': product.condition,
            'last_crawled': product.last_crawled.isoformat() if product.last_crawled else None,
            'current_price': {
                'price': float(latest_price.price) if latest_price else None,
                'currency': latest_price.currency if latest_price else None,
                'seller': latest_price.seller if latest_price else None,
                'availability': latest_price.availability if latest_price else None,
                'timestamp': latest_price.crawl_timestamp.isoformat() if latest_price else None
            } if latest_price else None
        }

        return JsonResponse(response_data)

    except AmazonProduct.DoesNotExist:
        return JsonResponse({'error': 'Product not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["GET"])
def get_price_history(request, asin):
    """دریافت تاریخچه قیمت"""
    try:
        days = int(request.GET.get('days', 30))
        history = crawler_service.get_product_history(asin.upper(), days)
        return JsonResponse(history)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["GET"])
def get_crawl_stats(request):
    """دریافت آمار crawlها"""
    try:
        days = int(request.GET.get('days', 7))
        stats = crawler_service.get_crawl_statistics(days)
        return JsonResponse(stats)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)