# amazon_app/views.py
from datetime import datetime, timedelta
from django.db.models import Count, Avg, Max, Min, Q
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .amazon_crawler import AmazonCrawlerService
from .permissions import IsAdminForAmazonAPI
from .models import AmazonProduct, AmazonProductPrice
from .serializers import (
    AmazonProductListSerializer,
    AmazonProductDetailSerializer,
    CrawlRequestSerializer,
    CrawlSingleRequestSerializer,
    VerifyMatchRequestSerializer,
    CrawlByURLRequestSerializer,
    PriceHistoryRequestSerializer,
    ProductStatsSerializer
)
from contract_manager.models import Product

crawler_service = AmazonCrawlerService()


class AmazonBaseAPIView(APIView):
    """کلاس پایه برای تمام APIهای آمازون - فقط برای Admin"""
    authentication_classes = [
        JWTAuthentication,  # اولویت با JWT
        # SessionAuthentication,  # سپس Session برای Swagger UI
        # BasicAuthentication,  # برای تست
    ]
    permission_classes = [IsAuthenticated, IsAdminForAmazonAPI]


class ListProductsAPIView(AmazonBaseAPIView):
    """لیست محصولات آمازون با فیلترهای مختلف - فقط برای Admin"""

    @swagger_auto_schema(
        operation_description="لیست محصولات آمازون با فیلترها و صفحه‌بندی (فقط Admin)",
        manual_parameters=[
            openapi.Parameter(
                'page',
                openapi.IN_QUERY,
                description="شماره صفحه",
                type=openapi.TYPE_INTEGER,
                default=1
            ),
            openapi.Parameter(
                'page_size',
                openapi.IN_QUERY,
                description="تعداد آیتم در هر صفحه",
                type=openapi.TYPE_INTEGER,
                default=20
            ),
            openapi.Parameter(
                'search',
                openapi.IN_QUERY,
                description="جستجو در عنوان، برند و ASIN",
                type=openapi.TYPE_STRING
            ),
            openapi.Parameter(
                'country_code',
                openapi.IN_QUERY,
                description="فیلتر بر اساس کد کشور (مثال: US, DE, FR)",
                type=openapi.TYPE_STRING
            ),
            openapi.Parameter(
                'category',
                openapi.IN_QUERY,
                description="فیلتر بر اساس دسته‌بندی",
                type=openapi.TYPE_STRING
            ),
            openapi.Parameter(
                'brand',
                openapi.IN_QUERY,
                description="فیلتر بر اساس برند",
                type=openapi.TYPE_STRING
            ),
            openapi.Parameter(
                'min_rating',
                openapi.IN_QUERY,
                description="حداقل رتبه (0-5)",
                type=openapi.TYPE_NUMBER,
                minimum=0,
                maximum=5
            ),
            openapi.Parameter(
                'min_reviews',
                openapi.IN_QUERY,
                description="حداقل تعداد نظرات",
                type=openapi.TYPE_INTEGER
            ),
            openapi.Parameter(
                'sort_by',
                openapi.IN_QUERY,
                description="مرتب‌سازی بر اساس (last_crawled, rating, review_count, price)",
                type=openapi.TYPE_STRING,
                enum=['last_crawled', 'rating', 'review_count', 'price']
            ),
            openapi.Parameter(
                'sort_order',
                openapi.IN_QUERY,
                description="ترتیب مرتب‌سازی (asc, desc)",
                type=openapi.TYPE_STRING,
                enum=['asc', 'desc'],
                default='desc'
            ),
            openapi.Parameter(
                'has_price',
                openapi.IN_QUERY,
                description="فقط محصولات با قیمت",
                type=openapi.TYPE_BOOLEAN
            ),
            openapi.Parameter(
                'days_since_last_crawl',
                openapi.IN_QUERY,
                description="حداکثر روز از آخرین crawl",
                type=openapi.TYPE_INTEGER
            ),
            openapi.Parameter(
                'asin_list',
                openapi.IN_QUERY,
                description="لیست ASINها (جدا شده با کاما)",
                type=openapi.TYPE_STRING
            ),
        ],
        responses={
            200: openapi.Response(
                description='لیست محصولات',
                examples={
                    'application/json': {
                        'success': True,
                        'count': 10,
                        'total_count': 100,
                        'total_pages': 5,
                        'current_page': 1,
                        'page_size': 20,
                        'next_page': 'http://example.com/api/amazon/products/?page=2',
                        'previous_page': None,
                        'filters': {
                            'country_code': 'US',
                            'sort_by': 'last_crawled',
                            'sort_order': 'desc'
                        },
                        'products': [
                            {
                                'asin': 'B08N5WRWNW',
                                'country_code': 'US',
                                'title': 'Example Product',
                                'brand': 'Example Brand',
                                'category': 'Electronics',
                                'rating': 4.5,
                                'review_count': 1234,
                                'image_url': 'http://example.com/image.jpg',
                                'current_price': {
                                    'price': 99.99,
                                    'currency': 'USD',
                                    'seller': 'Amazon',
                                    'timestamp': '2024-01-15T10:30:00Z'
                                }
                            }
                        ]
                    }
                }
            )
        }
    )
    def get(self, request):
        try:
            # دریافت پارامترها
            page = int(request.query_params.get('page', 1))
            page_size = int(request.query_params.get('page_size', 20))
            search = request.query_params.get('search', '').strip()
            country_code = request.query_params.get('country_code', '').strip()
            category = request.query_params.get('category', '').strip()
            brand = request.query_params.get('brand', '').strip()
            min_rating = request.query_params.get('min_rating')
            min_reviews = request.query_params.get('min_reviews')
            sort_by = request.query_params.get('sort_by', 'last_crawled')
            sort_order = request.query_params.get('sort_order', 'desc')
            has_price = request.query_params.get('has_price')
            days_since_last_crawl = request.query_params.get('days_since_last_crawl')
            asin_list = request.query_params.get('asin_list', '').strip()

            # شروع Query
            queryset = AmazonProduct.objects.all()

            # اعمال فیلترها
            if search:
                queryset = queryset.filter(
                    Q(title__icontains=search) |
                    Q(brand__icontains=search) |
                    Q(asin__icontains=search)
                )

            if country_code:
                queryset = queryset.filter(country_code=country_code.upper())

            if category:
                queryset = queryset.filter(category__icontains=category)

            if brand:
                queryset = queryset.filter(brand__icontains=brand)

            if min_rating:
                queryset = queryset.filter(rating__gte=float(min_rating))

            if min_reviews:
                queryset = queryset.filter(review_count__gte=int(min_reviews))

            if has_price == 'true':
                queryset = queryset.filter(prices__isnull=False).distinct()

            if days_since_last_crawl:
                cutoff_date = datetime.now() - timedelta(days=int(days_since_last_crawl))
                queryset = queryset.filter(last_crawled__gte=cutoff_date)

            if asin_list:
                asins = [asin.strip().upper() for asin in asin_list.split(',') if asin.strip()]
                queryset = queryset.filter(asin__in=asins)

            # مرتب‌سازی
            if sort_by == 'rating':
                sort_field = 'rating'
            elif sort_by == 'review_count':
                sort_field = 'review_count'
            elif sort_by == 'price':
                from django.db.models import Subquery, OuterRef
                latest_price = AmazonProductPrice.objects.filter(
                    product=OuterRef('pk')
                ).order_by('-crawl_timestamp')

                queryset = queryset.annotate(
                    latest_price_value=Subquery(latest_price.values('price')[:1])
                ).order_by(f'-latest_price_value' if sort_order == 'desc' else 'latest_price_value')
            else:
                sort_field = f'-{sort_by}' if sort_order == 'desc' else sort_by
                queryset = queryset.order_by(sort_field)

            # صفحه‌بندی
            total_count = queryset.count()
            total_pages = (total_count + page_size - 1) // page_size

            if page > total_pages:
                page = max(1, total_pages)

            start_index = (page - 1) * page_size
            end_index = start_index + page_size

            products = queryset[start_index:end_index]

            # سریالایز محصولات
            serializer = AmazonProductListSerializer(products, many=True)

            # ساخت URLهای صفحه‌بندی
            base_url = request.build_absolute_uri('/api/amazon/products/')
            query_params = request.GET.copy()

            next_page_url = None
            if page < total_pages:
                query_params['page'] = str(page + 1)
                next_page_url = f"{base_url}?{query_params.urlencode()}"

            previous_page_url = None
            if page > 1:
                query_params['page'] = str(page - 1)
                previous_page_url = f"{base_url}?{query_params.urlencode()}"

            # فیلترهای اعمال شده
            applied_filters = {
                'search': search if search else None,
                'country_code': country_code if country_code else None,
                'category': category if category else None,
                'brand': brand if brand else None,
                'min_rating': float(min_rating) if min_rating else None,
                'min_reviews': int(min_reviews) if min_reviews else None,
                'has_price': has_price == 'true' if has_price else None,
                'days_since_last_crawl': int(days_since_last_crawl) if days_since_last_crawl else None,
                'sort_by': sort_by,
                'sort_order': sort_order
            }

            return Response({
                'success': True,
                'count': len(serializer.data),
                'total_count': total_count,
                'total_pages': total_pages,
                'current_page': page,
                'page_size': page_size,
                'next_page': next_page_url,
                'previous_page': previous_page_url,
                'filters': {k: v for k, v in applied_filters.items() if v is not None},
                'products': serializer.data
            })

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class GetProductDetailAPIView(AmazonBaseAPIView):
    """دریافت اطلاعات کامل یک محصول با تاریخچه قیمت - فقط برای Admin"""

    @swagger_auto_schema(
        operation_description="دریافت اطلاعات کامل یک محصول با تمام جزئیات و تاریخچه قیمت (فقط Admin)",
        manual_parameters=[
            openapi.Parameter(
                'country_code',
                openapi.IN_QUERY,
                description="کد کشور (اگر محصول در چند کشور موجود باشد)",
                type=openapi.TYPE_STRING
            ),
            openapi.Parameter(
                'include_price_history',
                openapi.IN_QUERY,
                description="شامل تاریخچه قیمت (پیش‌فرض: true)",
                type=openapi.TYPE_BOOLEAN,
                default=True
            ),
            openapi.Parameter(
                'history_days',
                openapi.IN_QUERY,
                description="تعداد روزهای تاریخچه (پیش‌فرض: 90)",
                type=openapi.TYPE_INTEGER,
                default=90
            ),
            openapi.Parameter(
                'include_stats',
                openapi.IN_QUERY,
                description="شامل آمار قیمت",
                type=openapi.TYPE_BOOLEAN,
                default=True
            ),
            openapi.Parameter(
                'include_system_info',
                openapi.IN_QUERY,
                description="شامل اطلاعات سیستم ما",
                type=openapi.TYPE_BOOLEAN,
                default=True
            ),
        ],
        responses={
            200: openapi.Response(
                description='اطلاعات کامل محصول',
                examples={
                    'application/json': {
                        'asin': 'B08N5WRWNW',
                        'country_code': 'US',
                        'title': 'Example Product',
                        'brand': 'Example Brand',
                        'category': 'Electronics',
                        'rating': 4.5,
                        'review_count': 1234,
                        'image_url': 'http://example.com/image.jpg',
                        'current_price': {
                            'price': 99.99,
                            'currency': 'USD',
                            'seller': 'Amazon',
                            'timestamp': '2024-01-15T10:30:00Z'
                        },
                        'price_statistics': {
                            'all_time': {
                                'min_price': 89.99,
                                'max_price': 129.99,
                                'avg_price': 99.99,
                                'price_count': 50
                            }
                        }
                    }
                }
            )
        }
    )
    def get(self, request, asin):
        try:
            # پیدا کردن محصول
            country_code = request.query_params.get('country_code', '').strip().upper()

            queryset = AmazonProduct.objects.filter(asin=asin.upper())
            if country_code:
                queryset = queryset.filter(country_code=country_code)

            product = queryset.first()

            if not product:
                return Response(
                    {'error': 'Product not found'},
                    status=status.HTTP_404_NOT_FOUND
                )

            # سریالایز محصول با context برای پارامترهای query
            serializer = AmazonProductDetailSerializer(
                product,
                context={'request': request}
            )

            return Response(serializer.data)

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CrawlProductsAPIView(AmazonBaseAPIView):
    """Crawl کردن محصولات - فقط برای Admin"""

    @swagger_auto_schema(
        operation_description="Crawl کردن لیستی از محصولات آمازون (فقط Admin)",
        request_body=CrawlRequestSerializer,
        responses={
            200: openapi.Response(
                description='عملیات موفق',
                examples={
                    'application/json': {
                        'success': True,
                        'session_id': 'abc123',
                        'country': 'US',
                        'results': {
                            'total': 10,
                            'successful': 8,
                            'failed': 2,
                            'failed_asins': ['B001', 'B002']
                        }
                    }
                }
            ),
            400: openapi.Response(
                description='خطای اعتبارسنجی',
                examples={
                    'application/json': {
                        'error': {
                            'asins': ['This field is required.']
                        }
                    }
                }
            )
        }
    )
    def post(self, request):
        serializer = CrawlRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'error': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            data = serializer.validated_data
            results = crawler_service.crawl_products(
                data['asins'],
                data['country_code'],
                data['driver_name'],
                data.get('session_id')
            )

            if 'error' in results:
                return Response(
                    {'error': results['error']},
                    status=status.HTTP_400_BAD_REQUEST
                )

            return Response({
                'success': True,
                'session_id': results['session_id'],
                'country': results['country'],
                'results': {
                    'total': results['total'],
                    'successful': len(results['successful']),
                    'failed': len(results['failed']),
                    'failed_asins': results['failed']
                }
            })

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CrawlSingleProductAPIView(AmazonBaseAPIView):
    """Crawl کردن یک محصول - فقط برای Admin"""

    @swagger_auto_schema(
        operation_description="Crawl کردن یک محصول آمازون (فقط Admin)",
        request_body=CrawlSingleRequestSerializer,
        responses={
            200: openapi.Response(
                description='عملیات موفق',
                examples={
                    'application/json': {
                        'success': True,
                        'product': {
                            'asin': 'B08N5WRWNW',
                            'title': 'Example Product',
                            'price': 99.99,
                            'currency': 'USD'
                        }
                    }
                }
            )
        }
    )
    def post(self, request):
        serializer = CrawlSingleRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'error': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            data = serializer.validated_data
            product_identifier = data.get('asin') or data.get('url')

            product_data = crawler_service.crawl_single_product(
                product_identifier,
                data['country_code'],
                data['driver_name']
            )

            if product_data:
                return Response({
                    'success': True,
                    'product': product_data
                })
            else:
                return Response({
                    'success': False,
                    'error': 'Failed to crawl product'
                }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class GetPriceHistoryAPIView(AmazonBaseAPIView):
    """دریافت تاریخچه قیمت - فقط برای Admin"""

    @swagger_auto_schema(
        operation_description="دریافت تاریخچه قیمت یک محصول (فقط Admin)",
        manual_parameters=[
            openapi.Parameter(
                'country_code',
                openapi.IN_QUERY,
                description="کد کشور",
                type=openapi.TYPE_STRING
            ),
            openapi.Parameter(
                'days',
                openapi.IN_QUERY,
                description="تعداد روزهای گذشته (پیش‌فرض: 30)",
                type=openapi.TYPE_INTEGER,
                default=30
            ),
            openapi.Parameter(
                'granularity',
                openapi.IN_QUERY,
                description="دقت داده‌ها (daily, hourly, all)",
                type=openapi.TYPE_STRING,
                enum=['daily', 'hourly', 'all'],
                default='daily'
            ),
        ],
        responses={
            200: openapi.Response(
                description='تاریخچه قیمت',
                examples={
                    'application/json': {
                        'asin': 'B08N5WRWNW',
                        'country_code': 'US',
                        'period_days': 30,
                        'granularity': 'daily',
                        'statistics': {
                            'min_price': 89.99,
                            'max_price': 129.99,
                            'avg_price': 99.99,
                            'total_records': 30
                        },
                        'history': [
                            {
                                'date': '2024-01-01',
                                'avg_price': 99.99,
                                'min_price': 95.00,
                                'max_price': 105.00
                            }
                        ]
                    }
                }
            )
        }
    )
    def get(self, request, asin):
        try:
            serializer = PriceHistoryRequestSerializer(data=request.query_params)
            if not serializer.is_valid():
                return Response(
                    {'error': serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST
                )

            data = serializer.validated_data

            # پیدا کردن محصول
            queryset = AmazonProduct.objects.filter(asin=asin.upper())

            if data.get('country_code'):
                queryset = queryset.filter(country_code=data['country_code'].upper())

            product = queryset.first()

            if not product:
                return Response(
                    {'error': 'Product not found'},
                    status=status.HTTP_404_NOT_FOUND
                )

            # دریافت تاریخچه
            cutoff_date = datetime.now() - timedelta(days=data['days'])
            price_history = product.prices.filter(
                crawl_timestamp__gte=cutoff_date
            ).order_by('crawl_timestamp')

            if data['granularity'] == 'daily':
                from django.db.models.functions import TruncDate

                daily_prices = price_history.annotate(
                    date=TruncDate('crawl_timestamp')
                ).values('date').annotate(
                    min_price=Min('price'),
                    max_price=Max('price'),
                    avg_price=Avg('price'),
                    first_price=Min('crawl_timestamp'),
                    last_price=Max('crawl_timestamp'),
                    record_count=Count('id')
                ).order_by('date')

                history_data = [
                    {
                        'date': item['date'].isoformat(),
                        'min_price': float(item['min_price']),
                        'max_price': float(item['max_price']),
                        'avg_price': float(item['avg_price']),
                        'first_record_time': item['first_price'].isoformat(),
                        'last_record_time': item['last_price'].isoformat(),
                        'record_count': item['record_count']
                    }
                    for item in daily_prices
                ]

            elif data['granularity'] == 'hourly':
                from django.db.models.functions import TruncHour

                hourly_prices = price_history.annotate(
                    hour=TruncHour('crawl_timestamp')
                ).values('hour').annotate(
                    avg_price=Avg('price'),
                    record_count=Count('id')
                ).order_by('hour')

                history_data = [
                    {
                        'hour': item['hour'].isoformat(),
                        'avg_price': float(item['avg_price']),
                        'record_count': item['record_count']
                    }
                    for item in hourly_prices
                ]

            else:  # all
                history_data = [
                    {
                        'price': float(price.price),
                        'currency': price.currency,
                        'seller': price.seller,
                        'availability': price.availability,
                        'timestamp': price.crawl_timestamp.isoformat(),
                        'is_fba': price.is_fba,
                        'is_amazon': price.is_amazon
                    }
                    for price in price_history
                ]

            # آمار کلی
            stats = price_history.aggregate(
                min_price=Min('price'),
                max_price=Max('price'),
                avg_price=Avg('price'),
                total_records=Count('id'),
                first_record=Min('crawl_timestamp'),
                last_record=Max('crawl_timestamp'),
                unique_sellers=Count('seller', distinct=True)
            )

            response_data = {
                'asin': product.asin,
                'country_code': product.country_code,
                'product_title': product.title,
                'period_days': data['days'],
                'granularity': data['granularity'],
                'statistics': {
                    'min_price': float(stats['min_price']) if stats['min_price'] else None,
                    'max_price': float(stats['max_price']) if stats['max_price'] else None,
                    'avg_price': float(stats['avg_price']) if stats['avg_price'] else None,
                    'total_records': stats['total_records'] or 0,
                    'unique_sellers': stats['unique_sellers'] or 0,
                    'first_record': stats['first_record'].isoformat() if stats['first_record'] else None,
                    'last_record': stats['last_record'].isoformat() if stats['last_record'] else None,
                },
                'history': history_data,
                'record_count': len(history_data)
            }

            return Response(response_data)

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class GetCrawlStatsAPIView(AmazonBaseAPIView):
    """دریافت آمار crawlها - فقط برای Admin"""

    @swagger_auto_schema(
        operation_description="دریافت آمار crawlهای انجام شده (فقط Admin)",
        manual_parameters=[
            openapi.Parameter(
                'days',
                openapi.IN_QUERY,
                description="تعداد روزهای گذشته (پیش‌فرض: 7)",
                type=openapi.TYPE_INTEGER,
                default=7
            )
        ],
        responses={
            200: openapi.Response(
                description='آمار crawlها',
                examples={
                    'application/json': {
                        'total_crawls': 100,
                        'successful_crawls': 95,
                        'failed_crawls': 5,
                        'unique_products': 50,
                        'crawls_per_day': 14.3
                    }
                }
            )
        }
    )
    def get(self, request):
        try:
            serializer = ProductStatsSerializer(data=request.query_params)
            if not serializer.is_valid():
                return Response(
                    {'error': serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST
                )

            data = serializer.validated_data
            stats = crawler_service.get_crawl_statistics(data['days'])
            return Response(stats)

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class VerifyProductMatchAPIView(AmazonBaseAPIView):
    """تأیید تطابق URL با محصول - فقط برای Admin"""

    @swagger_auto_schema(
        operation_description="تأیید تطابق URL با ASIN محصول - بدون لود صفحه (فقط Admin)",
        request_body=VerifyMatchRequestSerializer,
        responses={
            200: openapi.Response(
                description='نتیجه تأیید',
                examples={
                    'application/json': {
                        'valid': True,
                        'actual_asin': 'B08N5WRWNW',
                        'expected_asin': 'B08N5WRWNW',
                        'match': True,
                        'url': 'https://www.amazon.com/dp/B08N5WRWNW'
                    }
                }
            )
        }
    )
    def post(self, request):
        serializer = VerifyMatchRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'error': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            data = serializer.validated_data
            verification_result = crawler_service.verify_product_match(
                data['url'],
                data['asin'].upper()
            )
            return Response(verification_result)

        except Exception as e:
            return Response({
                'valid': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CrawlByURLAPIView(AmazonBaseAPIView):
    """Crawl کردن محصول با URL - فقط برای Admin"""

    @swagger_auto_schema(
        operation_description="Crawl کردن محصول آمازون با URL (فقط Admin)",
        request_body=CrawlByURLRequestSerializer,
        responses={
            200: openapi.Response(
                description='اطلاعات محصول',
                examples={
                    'application/json': {
                        'success': True,
                        'product': {
                            'asin': 'B08N5WRWNW',
                            'title': 'Example Product',
                            'price': 99.99,
                            'currency': 'USD'
                        }
                    }
                }
            )
        }
    )
    def post(self, request):
        serializer = CrawlByURLRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'error': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            data = serializer.validated_data
            product_data = crawler_service.crawl_product_by_url(data['url'])

            if product_data:
                return Response({
                    'success': True,
                    'product': product_data
                })
            else:
                return Response({
                    'success': False,
                    'error': 'Failed to crawl product'
                }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
