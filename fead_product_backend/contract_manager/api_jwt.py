from django.utils import timezone
from rest_framework import viewsets, status, permissions, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

# تغییر import ها
from auth_app.models import SellerProfile, AgentProfile, AdminProfile, CustomUser
from django.conf import settings
from django.shortcuts import get_object_or_404
from django.db.models import Q
from .models import Product, Country, ProductChannel, ProductUpdateLog, ContractTemplate
from .serializers import CountrySerializer, ProductSerializer
from .services import ProductCrawlerService, ProductMessageService
from telegram_manager.models import TelegramChannel
from .api_permissions import (
    IsAdmin, IsAgent, IsSeller, IsAdminOrSeller,
    IsAdminOrAgent, IsAdminOrSelfSeller, IsAdminOrAgentForAssigned,
    IsAdminOrSellerOrAgentForAssigned, CanManageProductChannels
)
import uuid


class ProductChannelsAPIView(APIView):
    """دریافت کانال‌های قابل ارسال برای محصول خاص"""
    permission_classes = [permissions.IsAuthenticated, IsAdminOrSellerOrAgentForAssigned]

    def get(self, request, product_id):
        try:
            user = request.user
            product = None

            # پیدا کردن محصول بر اساس نوع کاربر
            if hasattr(user, 'admin_profile'):
                product = Product.objects.get(id=product_id)
            elif hasattr(user, 'seller_profile'):
                product = Product.objects.get(id=product_id, owner=user.seller_profile)
            elif hasattr(user, 'agent_profile'):
                # بررسی تأیید شدن Agent
                if not user.agent_profile.is_approved:
                    return Response({
                        'error': 'Agent not approved'
                    }, status=status.HTTP_403_FORBIDDEN)
                product = Product.objects.get(
                    id=product_id,
                    owner__in=user.agent_profile.managed_sellers.all()
                )
            else:
                return Response({
                    'error': 'Access denied'
                }, status=status.HTTP_403_FORBIDDEN)

            channels = product.get_related_channels()

            channel_data = [{
                'id': str(ch.id),
                'name': ch.name,
                'channel_id': ch.channel_id,
                'description': ch.description,
                'member_count': ch.member_count,
                'country': ch.country,
                'is_active': ch.is_active,
                'already_sent': ProductChannel.objects.filter(
                    product=product,
                    channel=ch,
                    status='sent'
                ).exists()
            } for ch in channels]

            return Response({
                'product_id': str(product_id),
                'product_asin': product.asin,
                'country': product.country.code,
                'channels': channel_data,
                'count': len(channel_data)
            })

        except Product.DoesNotExist:
            return Response({
                'error': 'Product not found or access denied'
            }, status=status.HTTP_404_NOT_FOUND)


class BulkRefreshAPIView(APIView):
    """بروزرسانی دسته‌ای محصولات"""
    permission_classes = [permissions.IsAuthenticated, IsAdminOrSellerOrAgentForAssigned]

    def post(self, request):
        product_ids = request.data.get('product_ids', [])
        seller_id = request.data.get('seller_id')  # برای ادمین/ایجنت

        if not product_ids:
            return Response({
                'error': 'product_ids is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        user = request.user
        products_query = Product.objects.filter(id__in=product_ids)

        # فیلتر بر اساس نوع کاربر
        if hasattr(user, 'seller_profile'):
            # بررسی تأیید شدن Seller
            if not user.seller_profile.is_approved:
                return Response({
                    'error': 'Seller not approved'
                }, status=status.HTTP_403_FORBIDDEN)
            products_query = products_query.filter(owner=user.seller_profile)
        elif hasattr(user, 'agent_profile'):
            # بررسی تأیید شدن Agent
            if not user.agent_profile.is_approved:
                return Response({
                    'error': 'Agent not approved'
                }, status=status.HTTP_403_FORBIDDEN)
            products_query = products_query.filter(owner__in=user.agent_profile.managed_sellers.all())
        # ادمین همه را می‌بیند، اما می‌تواند فیلتر کند
        elif hasattr(user, 'admin_profile') and seller_id:
            try:
                seller = SellerProfile.objects.get(id=seller_id)
                products_query = products_query.filter(owner=seller)
            except SellerProfile.DoesNotExist:
                pass

        products = list(products_query)

        if len(products) != len(product_ids):
            return Response({
                'error': 'Some products not found or access denied'
            }, status=status.HTTP_404_NOT_FOUND)

        crawler_service = ProductCrawlerService()
        results = []

        for product in products:
            success, message = crawler_service.refresh_product_data(product)
            results.append({
                'product_id': str(product.id),
                'asin': product.asin,
                'success': success,
                'message': message
            })

        return Response({
            'success': True,
            'message': f'Refreshed {len(results)} products',
            'results': results
        })


class BulkSendAPIView(APIView):
    """ارسال دسته‌ای محصولات به کانال‌ها"""
    permission_classes = [permissions.IsAuthenticated, IsAdminOrSellerOrAgentForAssigned]

    def post(self, request):
        product_ids = request.data.get('product_ids', [])
        channel_ids = request.data.get('channel_ids', [])
        seller_id = request.data.get('seller_id')  # برای ادمین/ایجنت

        if not product_ids or not channel_ids:
            return Response({
                'error': 'product_ids and channel_ids are required'
            }, status=status.HTTP_400_BAD_REQUEST)

        user = request.user
        products_query = Product.objects.filter(id__in=product_ids)

        # فیلتر بر اساس نوع کاربر
        if hasattr(user, 'seller_profile'):
            # بررسی تأیید شدن Seller
            if not user.seller_profile.is_approved:
                return Response({
                    'error': 'Seller not approved'
                }, status=status.HTTP_403_FORBIDDEN)
            products_query = products_query.filter(owner=user.seller_profile)
        elif hasattr(user, 'agent_profile'):
            # بررسی تأیید شدن Agent
            if not user.agent_profile.is_approved:
                return Response({
                    'error': 'Agent not approved'
                }, status=status.HTTP_403_FORBIDDEN)
            products_query = products_query.filter(owner__in=user.agent_profile.managed_sellers.all())
        # ادمین همه را می‌بیند، اما می‌تواند فیلتر کند
        elif hasattr(user, 'admin_profile') and seller_id:
            try:
                seller = SellerProfile.objects.get(id=seller_id)
                products_query = products_query.filter(owner=seller)
            except SellerProfile.DoesNotExist:
                pass

        products = list(products_query)

        if len(products) != len(product_ids):
            return Response({
                'error': 'Some products not found or access denied'
            }, status=status.HTTP_404_NOT_FOUND)

        message_service = ProductMessageService()
        all_results = []

        for product in products:
            send_results = message_service.send_product_to_channels(
                product=product,
                channel_ids=channel_ids
            )

            all_results.append({
                'product_id': str(product.id),
                'asin': product.asin,
                'title': product.title,
                'country': product.country.code,
                'results': send_results
            })

        return Response({
            'success': True,
            'message': f'Sent {len(all_results)} products to channels',
            'results': all_results
        })


class ProductViewSet(viewsets.ModelViewSet):
    """ViewSet برای مدیریت محصولات با JWT"""
    permission_classes = [permissions.IsAuthenticated, IsAdminOrSellerOrAgentForAssigned]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Product.objects.none()

        user = self.request.user

        # اگر Admin است، همه محصولات را ببیند
        if hasattr(user, 'admin_profile'):
            return Product.objects.all().select_related(
                'country', 'amazon_product', 'owner'
            ).order_by('-created_at')

        # اگر Seller است، فقط محصولات خودش
        if hasattr(user, 'seller_profile'):
            # بررسی تأیید شدن Seller
            if not user.seller_profile.is_approved:
                return Product.objects.none()
            return Product.objects.filter(owner=user.seller_profile).select_related(
                'country', 'amazon_product'
            ).order_by('-created_at')

        # اگر Agent است، محصولات فروشندگان اختصاص‌یافته
        if hasattr(user, 'agent_profile'):
            # بررسی تأیید شدن Agent
            if not user.agent_profile.is_approved:
                return Product.objects.none()
            assigned_sellers = user.agent_profile.managed_sellers.all()
            return Product.objects.filter(owner__in=assigned_sellers).select_related(
                'country', 'amazon_product', 'owner'
            ).order_by('-created_at')

        return Product.objects.none()

    def get_serializer_class(self):
        from .serializers import ProductSerializer
        return ProductSerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated(), IsAdminOrSeller()]
        return [permissions.IsAuthenticated(), IsAdminOrSellerOrAgentForAssigned()]

    def perform_create(self, serializer):
        """تعیین owner هنگام ایجاد محصول"""
        user = self.request.user
        data = self.request.data

        # تعیین owner محصول
        owner = None

        if hasattr(user, 'admin_profile'):
            # ادمین می‌تواند Seller مشخص کند
            seller_id = data.get('seller_id')
            if seller_id:
                try:
                    owner = SellerProfile.objects.get(id=seller_id)
                except SellerProfile.DoesNotExist:
                    raise serializers.ValidationError({'seller_id': 'Seller not found'})
            else:
                raise serializers.ValidationError({'seller_id': 'seller_id is required for admin users'})

        elif hasattr(user, 'seller_profile'):
            # بررسی تأیید شدن Seller
            if not user.seller_profile.is_approved:
                raise serializers.ValidationError({'detail': 'Seller not approved'})
            # Seller فقط می‌تواند برای خودش محصول ایجاد کند
            owner = user.seller_profile

        elif hasattr(user, 'agent_profile'):
            # بررسی تأیید شدن Agent
            if not user.agent_profile.is_approved:
                raise serializers.ValidationError({'detail': 'Agent not approved'})
            # Agent می‌تواند برای فروشندگان اختصاص‌یافته محصول ایجاد کند
            seller_id = data.get('seller_id')
            if seller_id:
                try:
                    seller = SellerProfile.objects.get(id=seller_id)
                    # بررسی اینکه فروشنده به این Agent اختصاص داده شده باشد
                    if seller not in user.agent_profile.managed_sellers.all():
                        raise serializers.ValidationError({'seller_id': 'Seller is not assigned to this agent'})
                    owner = seller
                except SellerProfile.DoesNotExist:
                    raise serializers.ValidationError({'seller_id': 'Seller not found'})
            else:
                raise serializers.ValidationError({'seller_id': 'seller_id is required for agent users'})

        serializer.save(owner=owner)

    @action(detail=True, methods=['post'])
    def refresh(self, request, pk=None):
        """بروزرسانی داده‌های محصول از آمازون"""
        product = self.get_object()
        crawler_service = ProductCrawlerService()

        success, message = crawler_service.refresh_product_data(product)

        if success:
            # لاگ تغییرات
            ProductUpdateLog.objects.create(
                product=product,
                update_type='info_update',
                description=f'Product refreshed via API: {message}',
                created_by=request.user
            )

            return Response({
                'success': True,
                'message': message,
                'product': self.get_serializer(product).data
            })
        else:
            return Response({
                'error': message
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def send_to_channels(self, request, pk=None):
        """ارسال محصول به کانال‌های تلگرام"""
        product = self.get_object()
        channel_ids = request.data.get('channel_ids', [])
        force_resend = request.data.get('force_resend', False)

        message_service = ProductMessageService()

        if force_resend:
            # حذف پیام‌های قبلی
            message_service.delete_telegram_messages(product)

        results = message_service.send_product_to_channels(
            product=product,
            channel_ids=channel_ids
        )

        # لاگ
        ProductUpdateLog.objects.create(
            product=product,
            update_type='telegram_update',
            description=f'Product sent to {len(results["successful"])} channels',
            affected_channels=results['successful'],
            telegram_updates_sent=True,
            created_by=request.user
        )

        return Response({
            'success': True,
            'message': f'Sent to {len(results["successful"])} channel(s)',
            'results': results
        })

    @action(detail=True, methods=['post'])
    def stop(self, request, pk=None):
        """متوقف کردن محصول"""
        product = self.get_object()
        product.stop_all_messages()

        # لاگ
        ProductUpdateLog.objects.create(
            product=product,
            update_type='status_change',
            old_data={'is_stopped': False},
            new_data={'is_stopped': True},
            description='Product stopped via API',
            created_by=request.user
        )

        return Response({
            'success': True,
            'message': 'Product and all messages stopped'
        })

    @action(detail=True, methods=['post'])
    def resume(self, request, pk=None):
        """ادامه دادن محصول"""
        product = self.get_object()
        product.resume_all_messages()

        # لاگ
        ProductUpdateLog.objects.create(
            product=product,
            update_type='status_change',
            old_data={'is_stopped': True},
            new_data={'is_stopped': False},
            description='Product resumed via API',
            created_by=request.user
        )

        return Response({
            'success': True,
            'message': 'Product and all messages resumed'
        })

    @action(detail=False, methods=['post'])
    def bulk_actions(self, request):
        """عملیات دسته‌ای روی محصولات"""
        action_type = request.data.get('action')
        product_ids = request.data.get('product_ids', [])
        seller_id = request.data.get('seller_id')  # برای ادمین/ایجنت

        if not action_type or not product_ids:
            return Response({
                'error': 'action and product_ids are required'
            }, status=status.HTTP_400_BAD_REQUEST)

        user = request.user
        products_query = Product.objects.filter(id__in=product_ids)

        # فیلتر بر اساس نوع کاربر
        if hasattr(user, 'seller_profile'):
            # بررسی تأیید شدن Seller
            if not user.seller_profile.is_approved:
                return Response({
                    'error': 'Seller not approved'
                }, status=status.HTTP_403_FORBIDDEN)
            products_query = products_query.filter(owner=user.seller_profile)
        elif hasattr(user, 'agent_profile'):
            # بررسی تأیید شدن Agent
            if not user.agent_profile.is_approved:
                return Response({
                    'error': 'Agent not approved'
                }, status=status.HTTP_403_FORBIDDEN)
            products_query = products_query.filter(owner__in=user.agent_profile.managed_sellers.all())
        # ادمین همه را می‌بیند، اما می‌تواند فیلتر کند
        elif hasattr(user, 'admin_profile') and seller_id:
            try:
                seller = SellerProfile.objects.get(id=seller_id)
                products_query = products_query.filter(owner=seller)
            except SellerProfile.DoesNotExist:
                pass

        products = list(products_query)

        if len(products) != len(product_ids):
            return Response({
                'error': 'Some products not found or access denied'
            }, status=status.HTTP_404_NOT_FOUND)

        if action_type == 'refresh':
            crawler_service = ProductCrawlerService()
            results = []

            for product in products:
                success, message = crawler_service.refresh_product_data(product)
                results.append({
                    'product_id': str(product.id),
                    'asin': product.asin,
                    'success': success,
                    'message': message
                })

            return Response({
                'success': True,
                'message': f'Refreshed {len(results)} products',
                'results': results
            })

        elif action_type == 'send_to_channels':
            channel_ids = request.data.get('channel_ids', [])
            message_service = ProductMessageService()

            results = []
            for product in products:
                send_results = message_service.send_product_to_channels(
                    product=product,
                    channel_ids=channel_ids
                )

                results.append({
                    'product_id': str(product.id),
                    'asin': product.asin,
                    'results': send_results
                })

            return Response({
                'success': True,
                'message': f'Sent {len(results)} products to channels',
                'results': results
            })

        elif action_type == 'stop':
            for product in products:
                product.stop_all_messages()

            return Response({
                'success': True,
                'message': f'Stopped {len(products)} products'
            })

        elif action_type == 'resume':
            for product in products:
                product.resume_all_messages()

            return Response({
                'success': True,
                'message': f'Resumed {len(products)} products'
            })

        else:
            return Response({
                'error': f'Unknown action: {action_type}'
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def assign_to_seller(self, request, pk=None):
        """اختصاص محصول به Seller دیگر (فقط برای Admin)"""
        if not hasattr(request.user, 'admin_profile'):
            return Response({
                'error': 'Only admin can assign products'
            }, status=status.HTTP_403_FORBIDDEN)

        product = self.get_object()
        seller_id = request.data.get('seller_id')

        if not seller_id:
            return Response({
                'error': 'seller_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            seller = SellerProfile.objects.get(id=seller_id)
        except SellerProfile.DoesNotExist:
            return Response({
                'error': 'Seller not found'
            }, status=status.HTTP_404_NOT_FOUND)

        old_owner = product.owner
        product.owner = seller
        product.save()

        # لاگ تغییرات
        ProductUpdateLog.objects.create(
            product=product,
            update_type='owner_change',
            old_data={'owner': str(old_owner.id) if old_owner else None},
            new_data={'owner': str(seller.id)},
            description=f'Product ownership changed from {old_owner} to {seller}',
            created_by=request.user
        )

        return Response({
            'success': True,
            'message': f'Product assigned to {seller.company_name}',
            'previous_owner': str(old_owner.id) if old_owner else None,
            'new_owner': str(seller.id)
        })

    def create(self, request, *args, **kwargs):
        """ایجاد محصول جدید"""
        data = request.data

        # بررسی فیلدهای ضروری
        asin = data.get('asin')
        url = data.get('url')
        country_code = data.get('country_code', 'US')

        if not (asin or url):
            return Response({
                'error': 'Either ASIN or URL is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        # بررسی کشور
        try:
            country = Country.objects.get(code=country_code, is_active=True)
        except Country.DoesNotExist:
            return Response({
                'error': f'Country {country_code} not found or inactive'
            }, status=status.HTTP_400_BAD_REQUEST)

        # استفاده از سرویس کراولر
        crawler_service = ProductCrawlerService()

        try:
            # ایجاد محصول با استفاده از serializer
            serializer = self.get_serializer(data=data)
            if serializer.is_valid():
                # ذخیره محصول (owner در perform_create تنظیم می‌شود)
                product = serializer.save(country=country)

                # کراول اطلاعات محصول
                if url:
                    success, message = crawler_service.refresh_product_data(product)
                else:
                    success, message = crawler_service.refresh_product_data(product)

                if success:
                    # لاگ
                    ProductUpdateLog.objects.create(
                        product=product,
                        update_type='info_update',
                        description=f'Product created via API: {message}',
                        created_by=request.user
                    )

                    # ارسال خودکار به کانال‌ها
                    auto_send = data.get('auto_send', False)
                    channel_ids = data.get('channel_ids', [])

                    response_data = {
                        'success': True,
                        'message': f'Product created: {message}',
                        'product': self.get_serializer(product).data
                    }

                    if auto_send and product.country.get_related_channels().exists():
                        message_service = ProductMessageService()
                        send_results = message_service.send_product_to_channels(
                            product=product,
                            channel_ids=channel_ids
                        )

                        response_data['telegram_results'] = send_results
                        response_data['message'] = f'Product created and sent to channels: {message}'

                    return Response(response_data, status=status.HTTP_201_CREATED)
                else:
                    # اگر کراول موفق نبود، محصول را حذف کن
                    product.delete()
                    return Response({
                        'error': f'Failed to crawl product data: {message}'
                    }, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({
                    'error': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ChannelAPIView(APIView):
    """API برای مدیریت کانال‌ها"""
    permission_classes = [permissions.IsAuthenticated, IsAdminOrSellerOrAgentForAssigned]

    def get(self, request):
        """دریافت کانال‌های کشورهای مختلف"""
        # کشورهای فعال
        countries = Country.objects.filter(is_active=True)

        country_channels = []
        for country in countries:
            channels = TelegramChannel.objects.filter(
                country=country.code,
                is_active=True
            )

            country_channels.append({
                'country': {
                    'code': country.code,
                    'name': country.name,
                    'amazon_domain': country.amazon_domain
                },
                'channels': [{
                    'id': str(ch.id),
                    'name': ch.name,
                    'channel_id': ch.channel_id,
                    'description': ch.description,
                    'member_count': ch.member_count
                } for ch in channels],
                'has_channels': channels.exists()
            })

        return Response({
            'countries': country_channels,
            'total_countries': len(country_channels)
        })

    def post(self, request):
        """مدیریت کانال برای محصول خاص"""
        product_id = request.data.get('product_id')
        channel_id = request.data.get('channel_id')
        action = request.data.get('action')

        if not all([product_id, channel_id, action]):
            return Response({
                'error': 'Missing required fields: product_id, channel_id, action'
            }, status=status.HTTP_400_BAD_REQUEST)

        user = request.user

        try:
            product = Product.objects.get(id=product_id)
            channel = TelegramChannel.objects.get(id=channel_id, is_active=True)

            # بررسی دسترسی کاربر به محصول
            if hasattr(user, 'seller_profile'):
                # بررسی تأیید شدن Seller
                if not user.seller_profile.is_approved:
                    return Response({
                        'error': 'Seller not approved'
                    }, status=status.HTTP_403_FORBIDDEN)
                if product.owner != user.seller_profile:
                    return Response({
                        'error': 'Access denied'
                    }, status=status.HTTP_403_FORBIDDEN)
            elif hasattr(user, 'agent_profile'):
                # بررسی تأیید شدن Agent
                if not user.agent_profile.is_approved:
                    return Response({
                        'error': 'Agent not approved'
                    }, status=status.HTTP_403_FORBIDDEN)
                if product.owner not in user.agent_profile.managed_sellers.all():
                    return Response({
                        'error': 'Access denied'
                    }, status=status.HTTP_403_FORBIDDEN)
            # ادمین دسترسی کامل دارد

        except Product.DoesNotExist:
            return Response({
                'error': 'Product not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except TelegramChannel.DoesNotExist:
            return Response({
                'error': 'Channel not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except ValueError:
            return Response({
                'error': 'Invalid ID format'
            }, status=status.HTTP_400_BAD_REQUEST)

        if action == 'enable':
            # فعال کردن ارسال به کانال
            product_channel, created = ProductChannel.objects.get_or_create(
                product=product,
                channel=channel,
                defaults={
                    'should_send': True,
                    'status': 'draft'
                }
            )

            if not created:
                product_channel.should_send = True
                product_channel.save()

            return Response({
                'success': True,
                'message': f'Channel {channel.name} enabled for product',
                'product_channel_id': str(product_channel.id)
            })

        elif action == 'disable':
            # غیرفعال کردن ارسال به کانال
            try:
                product_channel = ProductChannel.objects.get(
                    product=product,
                    channel=channel
                )
                product_channel.should_send = False
                product_channel.save()

                return Response({
                    'success': True,
                    'message': f'Channel {channel.name} disabled for product'
                })
            except ProductChannel.DoesNotExist:
                return Response({
                    'success': True,
                    'message': f'Channel {channel.name} was not enabled for product'
                })

        elif action == 'update':
            # بروزرسانی تنظیمات کانال
            auto_update = request.data.get('auto_update', True)
            notify_on_change = request.data.get('notify_on_change', True)

            product_channel, created = ProductChannel.objects.get_or_create(
                product=product,
                channel=channel,
                defaults={
                    'auto_update': auto_update,
                    'notify_on_change': notify_on_change
                }
            )

            if not created:
                product_channel.auto_update = auto_update
                product_channel.notify_on_change = notify_on_change
                product_channel.save()

            return Response({
                'success': True,
                'message': f'Channel settings updated for {channel.name}',
                'settings': {
                    'auto_update': product_channel.auto_update,
                    'notify_on_change': product_channel.notify_on_change
                }
            })

        else:
            return Response({
                'error': f'Unknown action: {action}'
            }, status=status.HTTP_400_BAD_REQUEST)


class CountriesAPIView(APIView):
    """API برای دریافت کشورها"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """دریافت لیست کشورهای فعال"""
        countries = Country.objects.filter(
            is_active=True,
            is_available_for_products=True
        ).order_by('display_order', 'name')

        country_list = [{
            'code': country.code,
            'name': country.name,
            'amazon_domain': country.amazon_domain,
            'currency': country.get_currency_code(),
            'has_channels': country.get_related_channels().exists()
        } for country in countries]

        return Response({
            'countries': country_list,
            'count': len(country_list)
        })


class VerifyURLAPIView(APIView):
    """API برای تأیید URL محصول"""
    permission_classes = [permissions.IsAuthenticated, IsAdminOrSeller]

    def post(self, request):
        """تأیید URL محصول"""
        url = request.data.get('url')

        if not url:
            return Response({
                'error': 'URL is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        # استفاده از سرویس کراولر برای تأیید
        crawler_service = ProductCrawlerService()

        # تشخیص کشور از URL
        country_code = crawler_service._detect_country_from_url(url)

        # کراول اطلاعات پایه
        crawled_data = crawler_service.amazon_crawler.crawl_product_by_url(url)

        if not crawled_data:
            return Response({
                'valid': False,
                'error': 'Could not access product information'
            }, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            'valid': True,
            'asin': crawled_data.get('asin'),
            'title': crawled_data.get('title'),
            'country': country_code,
            'price': crawled_data.get('price'),
            'currency': crawled_data.get('currency'),
            'availability': crawled_data.get('availability'),
            'image_url': crawled_data.get('image_url')
        })


class ProductMessagesAPIView(APIView):
    """API برای مدیریت پیام‌های محصول"""
    permission_classes = [permissions.IsAuthenticated, IsAdminOrSellerOrAgentForAssigned]

    def get(self, request, product_id):
        """دریافت پیام‌های محصول"""
        user = request.user

        try:
            product = Product.objects.get(id=product_id)

            # بررسی دسترسی
            if hasattr(user, 'seller_profile'):
                # بررسی تأیید شدن Seller
                if not user.seller_profile.is_approved:
                    return Response({
                        'error': 'Seller not approved'
                    }, status=status.HTTP_403_FORBIDDEN)
                if product.owner != user.seller_profile:
                    return Response({
                        'error': 'Access denied'
                    }, status=status.HTTP_403_FORBIDDEN)
            elif hasattr(user, 'agent_profile'):
                # بررسی تأیید شدن Agent
                if not user.agent_profile.is_approved:
                    return Response({
                        'error': 'Agent not approved'
                    }, status=status.HTTP_403_FORBIDDEN)
                if product.owner not in user.agent_profile.managed_sellers.all():
                    return Response({
                        'error': 'Access denied'
                    }, status=status.HTTP_403_FORBIDDEN)
            # ادمین دسترسی کامل دارد

        except Product.DoesNotExist:
            return Response({
                'error': 'Product not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except ValueError:
            return Response({
                'error': 'Invalid product ID'
            }, status=status.HTTP_400_BAD_REQUEST)

        product_channels = ProductChannel.objects.filter(
            product=product
        ).select_related('channel')

        messages = [{
            'id': str(pc.id),
            'channel': {
                'id': str(pc.channel.id),
                'name': pc.channel.name
            },
            'telegram_message_id': pc.telegram_message_id,
            'status': pc.status,
            'sent_at': pc.sent_at.isoformat() if pc.sent_at else None,
            'views': pc.view_count,
            'clicks': pc.click_count,
            'message_preview': pc.telegram_message_text[:100] + '...' if len(
                pc.telegram_message_text) > 100 else pc.telegram_message_text
        } for pc in product_channels]

        return Response({
            'messages': messages,
            'count': len(messages)
        })

    def post(self, request, product_id):
        """ویرایش پیام خاص"""
        user = request.user
        message_id = request.data.get('message_id')
        new_text = request.data.get('message_text')

        if not message_id or not new_text:
            return Response({
                'error': 'message_id and message_text are required'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            product = Product.objects.get(id=product_id)
            product_channel = ProductChannel.objects.get(
                id=message_id,
                product=product
            )

            # بررسی دسترسی
            if hasattr(user, 'seller_profile'):
                # بررسی تأیید شدن Seller
                if not user.seller_profile.is_approved:
                    return Response({
                        'error': 'Seller not approved'
                    }, status=status.HTTP_403_FORBIDDEN)
                if product.owner != user.seller_profile:
                    return Response({
                        'error': 'Access denied'
                    }, status=status.HTTP_403_FORBIDDEN)
            elif hasattr(user, 'agent_profile'):
                # بررسی تأیید شدن Agent
                if not user.agent_profile.is_approved:
                    return Response({
                        'error': 'Agent not approved'
                    }, status=status.HTTP_403_FORBIDDEN)
                if product.owner not in user.agent_profile.managed_sellers.all():
                    return Response({
                        'error': 'Access denied'
                    }, status=status.HTTP_403_FORBIDDEN)
            # ادمین دسترسی کامل دارد

        except Product.DoesNotExist:
            return Response({
                'error': 'Product not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except ProductChannel.DoesNotExist:
            return Response({
                'error': 'Message not found'
            }, status=status.HTTP_404_NOT_FOUND)

        # ویرایش در تلگرام
        message_service = ProductMessageService()
        success, error = message_service.telegram_service.edit_message(
            product_channel.channel.channel_id,
            product_channel.telegram_message_id,
            new_text
        )

        if success:
            product_channel.telegram_message_text = new_text
            product_channel.mark_as_edited()

            return Response({
                'success': True,
                'message': 'Message updated successfully'
            })
        else:
            return Response({
                'error': f'Failed to update message: {error}'
            }, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, product_id):
        """حذف پیام خاص"""
        user = request.user
        message_id = request.data.get('message_id')

        if not message_id:
            return Response({
                'error': 'message_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            product = Product.objects.get(id=product_id)
            product_channel = ProductChannel.objects.get(
                id=message_id,
                product=product
            )

            # بررسی دسترسی
            if hasattr(user, 'seller_profile'):
                # بررسی تأیید شدن Seller
                if not user.seller_profile.is_approved:
                    return Response({
                        'error': 'Seller not approved'
                    }, status=status.HTTP_403_FORBIDDEN)
                if product.owner != user.seller_profile:
                    return Response({
                        'error': 'Access denied'
                    }, status=status.HTTP_403_FORBIDDEN)
            elif hasattr(user, 'agent_profile'):
                # بررسی تأیید شدن Agent
                if not user.agent_profile.is_approved:
                    return Response({
                        'error': 'Agent not approved'
                    }, status=status.HTTP_403_FORBIDDEN)
                if product.owner not in user.agent_profile.managed_sellers.all():
                    return Response({
                        'error': 'Access denied'
                    }, status=status.HTTP_403_FORBIDDEN)
            # ادمین دسترسی کامل دارد

        except Product.DoesNotExist:
            return Response({
                'error': 'Product not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except ProductChannel.DoesNotExist:
            return Response({
                'error': 'Message not found'
            }, status=status.HTTP_404_NOT_FOUND)

        # حذف از تلگرام
        message_service = ProductMessageService()
        if product_channel.telegram_message_id:
            message_service.telegram_service.delete_message(
                product_channel.channel.channel_id,
                product_channel.telegram_message_id
            )

        # حذف از دیتابیس
        product_channel.mark_as_deleted()

        return Response({
            'success': True,
            'message': 'Message deleted successfully'
        })


class SellerManagementAPIView(APIView):
    """مدیریت فروشندگان توسط ادمین"""
    permission_classes = [permissions.IsAuthenticated, IsAdmin]

    def get(self, request):
        """دریافت لیست فروشندگان"""
        sellers = SellerProfile.objects.all().select_related('user').order_by('-created_at')

        seller_list = []
        for seller in sellers:
            seller_list.append({
                'id': seller.id,
                'user_id': seller.user.id,
                'username': seller.user.username,
                'email': seller.user.email,
                'company_name': seller.company_name,
                'contact_email': seller.contact_email,
                'contact_phone': seller.contact_phone,
                'is_approved': seller.is_approved,
                'approved_by': seller.approved_by.username if seller.approved_by else None,
                'approved_at': seller.approved_at.isoformat() if seller.approved_at else None,
                'rating': seller.rating,
                'total_contracts': seller.total_contracts,
                'completed_contracts': seller.completed_contracts,
                'assigned_agent': seller.assigned_agent.id if seller.assigned_agent else None,
                'assigned_agent_name': seller.assigned_agent.company_name if seller.assigned_agent else None,
                'created_at': seller.created_at.isoformat(),
                'updated_at': seller.updated_at.isoformat()
            })

        return Response({
            'sellers': seller_list,
            'count': len(seller_list)
        })

    def post(self, request):
        """تأیید یا عدم تأیید فروشنده"""
        seller_id = request.data.get('seller_id')
        action = request.data.get('action')  # 'approve' یا 'disapprove'
        reason = request.data.get('reason', '')

        if not seller_id or not action:
            return Response({
                'error': 'seller_id and action are required'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            seller = SellerProfile.objects.get(id=seller_id)
        except SellerProfile.DoesNotExist:
            return Response({
                'error': 'Seller not found'
            }, status=status.HTTP_404_NOT_FOUND)

        if action == 'approve':
            seller.approve(request.user)
            message = 'Seller approved successfully'
        elif action == 'disapprove':
            seller.disapprove()
            message = 'Seller disapproved successfully'
        else:
            return Response({
                'error': 'Invalid action. Use "approve" or "disapprove"'
            }, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            'success': True,
            'message': message,
            'seller_id': seller.id,
            'is_approved': seller.is_approved
        })


class AgentManagementAPIView(APIView):
    """مدیریت نمایندگان توسط ادمین"""
    permission_classes = [permissions.IsAuthenticated, IsAdmin]

    def get(self, request):
        """دریافت لیست نمایندگان"""
        agents = AgentProfile.objects.all().select_related('user').order_by('-created_at')

        agent_list = []
        for agent in agents:
            agent_list.append({
                'id': agent.id,
                'user_id': agent.user.id,
                'username': agent.user.username,
                'email': agent.user.email,
                'agent_type': agent.agent_type,
                'agent_type_display': agent.get_agent_type_display(),
                'company_name': agent.company_name,
                'contact_email': agent.contact_email,
                'contact_phone': agent.contact_phone,
                'is_approved': agent.is_approved,
                'approved_by': agent.approved_by.username if agent.approved_by else None,
                'approved_at': agent.approved_at.isoformat() if agent.approved_at else None,
                'commission_rate': float(agent.commission_rate),
                'assigned_sellers_count': agent.assigned_sellers.count(),
                'created_at': agent.created_at.isoformat(),
                'updated_at': agent.updated_at.isoformat()
            })

        return Response({
            'agents': agent_list,
            'count': len(agent_list)
        })

    def post(self, request):
        """تأیید یا عدم تأیید نماینده"""
        agent_id = request.data.get('agent_id')
        action = request.data.get('action')  # 'approve' یا 'disapprove'
        reason = request.data.get('reason', '')

        if not agent_id or not action:
            return Response({
                'error': 'agent_id and action are required'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            agent = AgentProfile.objects.get(id=agent_id)
        except AgentProfile.DoesNotExist:
            return Response({
                'error': 'Agent not found'
            }, status=status.HTTP_404_NOT_FOUND)

        if action == 'approve':
            agent.approve(request.user)
            message = 'Agent approved successfully'
        elif action == 'disapprove':
            agent.disapprove()
            message = 'Agent disapproved successfully'
        else:
            return Response({
                'error': 'Invalid action. Use "approve" or "disapprove"'
            }, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            'success': True,
            'message': message,
            'agent_id': agent.id,
            'is_approved': agent.is_approved
        })


class DashboardStatsAPIView(APIView):
    """آمار داشبورد"""
    permission_classes = [permissions.IsAuthenticated, IsAdmin]

    def get(self, request):
        """دریافت آمار کلی"""
        # آمار کاربران
        total_users = CustomUser.objects.count()
        active_users = CustomUser.objects.filter(is_active=True).count()
        sellers_count = SellerProfile.objects.count()
        agents_count = AgentProfile.objects.count()
        admins_count = AdminProfile.objects.count()

        # آمار محصولات
        total_products = Product.objects.count()
        active_products = Product.objects.filter(is_active=True).count()
        stopped_products = Product.objects.filter(is_stopped=True).count()

        # آمار کانال‌ها
        from telegram_manager.models import TelegramChannel
        total_channels = TelegramChannel.objects.count()
        active_channels = TelegramChannel.objects.filter(is_active=True).count()

        # آمار کشورها
        total_countries = Country.objects.count()
        amazon_countries = Country.get_amazon_countries().count()

        # محصولات اخیر
        recent_products = Product.objects.all().order_by('-created_at')[:10]
        recent_products_data = ProductSerializer(recent_products, many=True).data

        # کاربران منتظر تأیید
        pending_sellers = SellerProfile.objects.filter(is_approved=False).count()
        pending_agents = AgentProfile.objects.filter(is_approved=False).count()

        return Response({
            'users': {
                'total': total_users,
                'active': active_users,
                'sellers': sellers_count,
                'agents': agents_count,
                'admins': admins_count,
                'pending_sellers': pending_sellers,
                'pending_agents': pending_agents
            },
            'products': {
                'total': total_products,
                'active': active_products,
                'stopped': stopped_products
            },
            'channels': {
                'total': total_channels,
                'active': active_channels
            },
            'countries': {
                'total': total_countries,
                'with_amazon': amazon_countries
            },
            'recent_products': recent_products_data,
            'timestamp': timezone.now().isoformat()
        })
