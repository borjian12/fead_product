# selenium_app/views.py
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
import json
from .models import SeleniumDriver, CrawlRequest, DriverSession
from .serializers import (
    SeleniumDriverSerializer,
    CrawlRequestSerializer,
    CrawlRequestCreateSerializer,
    DriverSessionSerializer
)
from .request_manager import SeleniumRequestManager

manager = SeleniumRequestManager()


# View برای لیست و ایجاد درایورها (فقط ادمین)
class SeleniumDriverListCreateView(generics.ListCreateAPIView):
    queryset = SeleniumDriver.objects.all()
    serializer_class = SeleniumDriverSerializer
    permission_classes = [IsAdminUser]


# View برای جزئیات، به‌روزرسانی و حذف درایور (فقط ادمین)
class SeleniumDriverDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = SeleniumDriver.objects.all()
    serializer_class = SeleniumDriverSerializer
    permission_classes = [IsAdminUser]
    lookup_field = 'name'


# View برای لیست تمام درخواست‌های کراول (فقط ادمین)
class CrawlRequestListView(generics.ListAPIView):
    queryset = CrawlRequest.objects.all().select_related('driver')
    serializer_class = CrawlRequestSerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        queryset = super().get_queryset()

        # فیلتر بر اساس وضعیت
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        # فیلتر بر اساس درایور
        driver_filter = self.request.query_params.get('driver')
        if driver_filter:
            queryset = queryset.filter(driver__name=driver_filter)

        # فیلتر بر اساس requester
        requester_filter = self.request.query_params.get('requester')
        if requester_filter:
            queryset = queryset.filter(requester__icontains=requester_filter)

        return queryset


# View برای جزئیات درخواست کراول (فقط ادمین)
class CrawlRequestDetailView(generics.RetrieveAPIView):
    queryset = CrawlRequest.objects.all().select_related('driver')
    serializer_class = CrawlRequestSerializer
    permission_classes = [IsAdminUser]
    lookup_field = 'request_id'


# View برای ارسال درخواست کراول جدید (با احراز هویت)
@api_view(['POST'])
@permission_classes([IsAdminUser])
def submit_crawl_request(request):
    """ثبت درخواست crawl جدید با سریالایزر"""
    serializer = CrawlRequestCreateSerializer(data=request.data)

    if serializer.is_valid():
        try:
            data = serializer.validated_data
            driver_name = data.get('driver_name', 'default')
            url = data.get('url')
            requester = data.get('requester', 'unknown')
            metadata = data.get('metadata', {})

            request_id = manager.submit_request(driver_name, url, requester, metadata)

            return Response({
                'request_id': request_id,
                'status': 'queued',
                'message': 'Request submitted successfully'
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# View برای دریافت وضعیت درخواست کراول (با احراز هویت)
@api_view(['GET'])
@permission_classes([IsAdminUser])
def get_request_status(request, request_id):
    """دریافت وضعیت درخواست"""
    try:
        crawl_request = CrawlRequest.objects.get(request_id=request_id)
        serializer = CrawlRequestSerializer(crawl_request)
        return Response(serializer.data)

    except CrawlRequest.DoesNotExist:
        return Response({'error': 'Request not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# View برای لیست sessionهای فعال (فقط ادمین)
class DriverSessionListView(generics.ListAPIView):
    queryset = DriverSession.objects.all().select_related('driver')
    serializer_class = DriverSessionSerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        queryset = super().get_queryset()

        # فیلتر بر اساس فعال/غیرفعال بودن
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            is_active_bool = is_active.lower() in ('true', '1', 'yes')
            queryset = queryset.filter(is_active=is_active_bool)

        # فیلتر بر اساس درایور
        driver_filter = self.request.query_params.get('driver')
        if driver_filter:
            queryset = queryset.filter(driver__name=driver_filter)

        return queryset


# View برای جزئیات session (فقط ادمین)
class DriverSessionDetailView(generics.RetrieveAPIView):
    queryset = DriverSession.objects.all().select_related('driver')
    serializer_class = DriverSessionSerializer
    permission_classes = [IsAdminUser]
    lookup_field = 'session_id'


# View برای آمار و خلاصه (فقط ادمین)
@api_view(['GET'])
@permission_classes([IsAdminUser])
def get_crawl_stats(request):
    """دریافت آمار و خلاصه عملکرد"""
    try:
        total_requests = CrawlRequest.objects.count()
        completed_requests = CrawlRequest.objects.filter(status='COMPLETED').count()
        failed_requests = CrawlRequest.objects.filter(status='FAILED').count()
        pending_requests = CrawlRequest.objects.filter(status__in=['PENDING', 'QUEUED', 'PROCESSING']).count()

        active_drivers = SeleniumDriver.objects.filter(is_active=True).count()
        active_sessions = DriverSession.objects.filter(is_active=True).count()

        # آخرین 10 درخواست
        recent_requests = CrawlRequest.objects.all()[:10]
        recent_serializer = CrawlRequestSerializer(recent_requests, many=True)

        stats = {
            'total_requests': total_requests,
            'completed_requests': completed_requests,
            'failed_requests': failed_requests,
            'pending_requests': pending_requests,
            'success_rate': (completed_requests / total_requests * 100) if total_requests > 0 else 0,
            'active_drivers': active_drivers,
            'active_sessions': active_sessions,
            'recent_requests': recent_serializer.data
        }

        return Response(stats)

    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)