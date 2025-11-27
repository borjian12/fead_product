# selenium_app/views.py
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
from .request_manager import SeleniumRequestManager

manager = SeleniumRequestManager()


@csrf_exempt
@require_http_methods(["POST"])
def submit_crawl_request(request):
    """ثبت درخواست crawl جدید"""
    try:
        data = json.loads(request.body)
        driver_name = data.get('driver_name', 'default')
        url = data.get('url')
        requester = data.get('requester', 'unknown')
        metadata = data.get('metadata', {})

        if not url:
            return JsonResponse({'error': 'URL is required'}, status=400)

        request_id = manager.submit_request(driver_name, url, requester, metadata)

        return JsonResponse({
            'request_id': request_id,
            'status': 'queued',
            'message': 'Request submitted successfully'
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["GET"])
def get_request_status(request, request_id):
    """دریافت وضعیت درخواست"""
    try:
        from .models import CrawlRequest

        crawl_request = CrawlRequest.objects.get(request_id=request_id)

        response_data = {
            'request_id': crawl_request.request_id,
            'url': crawl_request.url,
            'status': crawl_request.status,
            'requester': crawl_request.requester,
            'created_at': crawl_request.created_at.isoformat(),
            'started_at': crawl_request.started_at.isoformat() if crawl_request.started_at else None,
            'completed_at': crawl_request.completed_at.isoformat() if crawl_request.completed_at else None,
        }

        if crawl_request.status == 'COMPLETED':
            response_data['html_content'] = crawl_request.html_content
        elif crawl_request.status == 'FAILED':
            response_data['error_message'] = crawl_request.error_message

        return JsonResponse(response_data)

    except CrawlRequest.DoesNotExist:
        return JsonResponse({'error': 'Request not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)