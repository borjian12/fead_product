## //telegram_manager/api_views.py
from rest_framework import viewsets, status, generics, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.utils import timezone
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User

from .models import TelegramChannel, TelegramMessage, MessageEditHistory, MessageSendingLog
from .serializers import (
    TelegramChannelSerializer, TelegramMessageSerializer,
    MessageEditHistorySerializer, MessageSendingLogSerializer,
    SendMessageSerializer, EditMessageSerializer,
    ReplyMessageSerializer, BulkSendSerializer
)
from .services import TelegramBotService


# Permission کلاس‌های
class IsOwnerOrAdmin(permissions.BasePermission):
    """اجازه دسترسی به مالک یا ادمین"""

    def has_object_permission(self, request, view, obj):
        if request.user.is_staff:
            return True
        return obj.created_by == request.user


# Telegram ویوهای اصلی
class TelegramChannelViewSet(viewsets.ModelViewSet):
    """ViewSet برای مدیریت کانال‌های تلگرام"""
    queryset = TelegramChannel.objects.all()
    serializer_class = TelegramChannelSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        """تنظیم permissions برای actions مختلف"""
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [IsAdminUser]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]

    def perform_create(self, serializer):
        serializer.save()

    def perform_update(self, serializer):
        serializer.save()

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def toggle_active(self, request, pk=None):
        """تغییر وضعیت فعال/غیرفعال کانال"""
        channel = self.get_object()
        channel.is_active = not channel.is_active
        channel.save()

        serializer = self.get_serializer(channel)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def active_channels(self, request):
        """دریافت کانال‌های فعال"""
        channels = self.queryset.filter(is_active=True)

        # فیلتر بر اساس کشور
        country = request.query_params.get('country', None)
        if country:
            channels = channels.filter(country=country)

        serializer = self.get_serializer(channels, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def channel_messages(self, request, pk=None):
        """دریافت پیام‌های یک کانال"""
        channel = self.get_object()
        messages = TelegramMessage.objects.filter(channel=channel)

        # فیلتر بر اساس وضعیت
        status_filter = request.query_params.get('status', None)
        if status_filter:
            messages = messages.filter(status=status_filter)

        serializer = TelegramMessageSerializer(messages, many=True)
        return Response(serializer.data)


class TelegramMessageViewSet(viewsets.ModelViewSet):
    """ViewSet برای مدیریت پیام‌ها"""
    queryset = TelegramMessage.objects.all()
    serializer_class = TelegramMessageSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()

        if self.request.user.is_staff:
            return queryset

        return queryset.filter(created_by=self.request.user)

    def get_permissions(self):
        """تنظیم permissions برای actions مختلف"""
        if self.action in ['destroy']:
            permission_classes = [IsOwnerOrAdmin]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['post'], permission_classes=[IsOwnerOrAdmin])
    def send(self, request, pk=None):
        """ارسال پیام به تلگرام"""
        message = self.get_object()

        if message.status == 'sent':
            return Response(
                {'error': 'این پیام قبلاً ارسال شده است.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if message.scheduled_time and message.scheduled_time > timezone.now():
            return Response(
                {'error': 'زمان ارسال پیام هنوز نرسیده است.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            bot_service = TelegramBotService()
            success, telegram_message_id, error = bot_service.send_message(
                channel_id=message.channel.channel_id,
                message_text=message.message_text,
                images=message.images,
                reply_to_message_id=message.reply_to_message_id
            )

            if success:
                message.status = 'sent'
                message.telegram_message_id = telegram_message_id
                message.sent_at = timezone.now()
                message.save()

                MessageSendingLog.objects.create(
                    message=message,
                    success=True,
                    telegram_message_id=telegram_message_id,
                    response_data={'success': True}
                )

                serializer = self.get_serializer(message)
                return Response(serializer.data)
            else:
                MessageSendingLog.objects.create(
                    message=message,
                    success=False,
                    error_message=error,
                    response_data={'error': error}
                )

                message.status = 'failed'
                message.save()

                return Response(
                    {'error': f'خطا در ارسال پیام: {error}'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        except Exception as e:
            return Response(
                {'error': f'خطای سیستمی: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'], permission_classes=[IsOwnerOrAdmin])
    def edit(self, request, pk=None):
        """ویرایش پیام در تلگرام"""
        message = self.get_object()

        if message.status != 'sent':
            return Response(
                {'error': 'فقط پیام‌های ارسال شده قابل ویرایش هستند.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = EditMessageSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        new_text = serializer.validated_data['new_message_text']
        new_images = serializer.validated_data.get('images', [])

        try:
            MessageEditHistory.objects.create(
                message=message,
                old_message_text=message.message_text,
                new_message_text=new_text,
                old_images=message.images,
                new_images=new_images,
                edited_by=request.user
            )

            bot_service = TelegramBotService()
            success, error = bot_service.edit_message(
                channel_id=message.channel.channel_id,
                message_id=message.telegram_message_id,
                new_text=new_text,
                images=new_images
            )

            if success:
                message.message_text = new_text
                message.images = new_images
                message.status = 'edited'
                message.save()

                history = MessageEditHistory.objects.filter(
                    message=message
                ).latest('edited_at')
                history.telegram_edit_success = True
                history.save()

                serializer = self.get_serializer(message)
                return Response(serializer.data)
            else:
                return Response(
                    {'error': f'خطا در ویرایش پیام: {error}'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        except Exception as e:
            return Response(
                {'error': f'خطای سیستمی: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'], permission_classes=[IsOwnerOrAdmin])
    def delete_telegram_message(self, request, pk=None):
        """حذف پیام از تلگرام"""
        message = self.get_object()

        if not message.telegram_message_id:
            return Response(
                {'error': 'این پیام هنوز در تلگرام ارسال نشده است.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            bot_service = TelegramBotService()
            success, error = bot_service.delete_message(
                channel_id=message.channel.channel_id,
                message_id=message.telegram_message_id
            )

            if success:
                return Response(
                    {'success': True, 'message': 'پیام با موفقیت حذف شد.'}
                )
            else:
                return Response(
                    {'error': f'خطا در حذف پیام: {error}'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        except Exception as e:
            return Response(
                {'error': f'خطای سیستمی: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'], permission_classes=[IsOwnerOrAdmin])
    def schedule(self, request, pk=None):
        """زمان‌بندی ارسال پیام"""
        message = self.get_object()

        schedule_time = request.data.get('schedule_time')
        if not schedule_time:
            return Response(
                {'error': 'زمان ارسال الزامی است.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            message.scheduled_time = schedule_time
            message.status = 'scheduled'
            message.save()

            serializer = self.get_serializer(message)
            return Response(serializer.data)

        except Exception as e:
            return Response(
                {'error': f'خطا در زمان‌بندی: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def my_messages(self, request):
        """دریافت پیام‌های کاربر جاری"""
        status_filter = request.query_params.get('status', None)

        if status_filter:
            messages = self.queryset.filter(
                created_by=request.user,
                status=status_filter
            )
        else:
            messages = self.queryset.filter(created_by=request.user)

        page = self.paginate_queryset(messages)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(messages, many=True)
        return Response(serializer.data)


class MessageEditHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet برای مشاهده تاریخچه ویرایش پیام‌ها"""
    queryset = MessageEditHistory.objects.all()
    serializer_class = MessageEditHistorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()

        if self.request.user.is_staff:
            return queryset

        return queryset.filter(edited_by=self.request.user)


class MessageSendingLogViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet برای مشاهده لاگ ارسال پیام‌ها"""
    queryset = MessageSendingLog.objects.all()
    serializer_class = MessageSendingLogSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()

        if self.request.user.is_staff:
            return queryset

        return queryset.filter(message__created_by=self.request.user)


# API Viewهای کمکی
class SendDirectMessageAPI(APIView):
    """ارسال مستقیم پیام بدون ذخیره در دیتابیس"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = SendMessageSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data

        try:
            channel = TelegramChannel.objects.get(id=data['channel_id'])
            bot_service = TelegramBotService()

            success, telegram_message_id, error = bot_service.send_message(
                channel_id=channel.channel_id,
                message_text=data['message_text'],
                images=data['images'],
                reply_to_message_id=data.get('reply_to_message_id')
            )

            if success:
                return Response({
                    'success': True,
                    'telegram_message_id': telegram_message_id,
                    'message': 'پیام با موفقیت ارسال شد.'
                })
            else:
                return Response({
                    'success': False,
                    'error': error
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        except TelegramChannel.DoesNotExist:
            return Response(
                {'error': 'کانال مورد نظر یافت نشد.'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': f'خطای سیستمی: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class BulkSendAPI(APIView):
    """ارسال پیام به چند کانال به صورت همزمان"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = BulkSendSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data

        try:
            channels = TelegramChannel.objects.filter(
                id__in=data['channel_ids'],
                is_active=True
            )

            if not channels.exists():
                return Response(
                    {'error': 'هیچ کانال فعالی یافت نشد.'},
                    status=status.HTTP_404_NOT_FOUND
                )

            results = []
            bot_service = TelegramBotService()

            for channel in channels:
                try:
                    success, telegram_message_id, error = bot_service.send_message(
                        channel_id=channel.channel_id,
                        message_text=data['message_text'],
                        images=data['images']
                    )

                    results.append({
                        'channel_id': str(channel.id),
                        'channel_name': channel.name,
                        'success': success,
                        'telegram_message_id': telegram_message_id,
                        'error': error if not success else None
                    })

                except Exception as e:
                    results.append({
                        'channel_id': str(channel.id),
                        'channel_name': channel.name,
                        'success': False,
                        'error': str(e)
                    })

            return Response({
                'total_channels': len(channels),
                'success_count': len([r for r in results if r['success']]),
                'failed_count': len([r for r in results if not r['success']]),
                'results': results
            })

        except Exception as e:
            return Response(
                {'error': f'خطای سیستمی: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class BotInfoAPI(APIView):
    """دریافت اطلاعات بات تلگرام"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            bot_service = TelegramBotService()
            bot_info = bot_service.get_bot_info()

            if bot_info:
                return Response({
                    'success': True,
                    'bot_info': {
                        'id': bot_info['id'],
                        'username': bot_info['username'],
                        'first_name': bot_info['first_name'],
                        'can_join_groups': bot_info.get('can_join_groups', False),
                        'can_read_all_group_messages': bot_info.get('can_read_all_group_messages', False),
                        'supports_inline_queries': bot_info.get('supports_inline_queries', False)
                    }
                })
            else:
                return Response({
                    'success': False,
                    'error': 'دریافت اطلاعات بات با خطا مواجه شد.'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        except Exception as e:
            return Response({
                'success': False,
                'error': f'خطای سیستمی: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_dashboard_stats(request):
    """آمار داشبورد"""
    user = request.user

    try:
        # آمار کانال‌ها
        if user.is_staff:
            total_channels = TelegramChannel.objects.count()
            active_channels = TelegramChannel.objects.filter(is_active=True).count()
        else:
            total_channels = 0
            active_channels = 0

        # آمار پیام‌ها
        if user.is_staff:
            total_messages = TelegramMessage.objects.count()
            sent_messages = TelegramMessage.objects.filter(status='sent').count()
            scheduled_messages = TelegramMessage.objects.filter(status='scheduled').count()
            failed_messages = TelegramMessage.objects.filter(status='failed').count()
        else:
            total_messages = TelegramMessage.objects.filter(created_by=user).count()
            sent_messages = TelegramMessage.objects.filter(created_by=user, status='sent').count()
            scheduled_messages = TelegramMessage.objects.filter(created_by=user, status='scheduled').count()
            failed_messages = TelegramMessage.objects.filter(created_by=user, status='failed').count()

        # آمار ارسال امروز
        today = timezone.now().date()
        if user.is_staff:
            today_messages = TelegramMessage.objects.filter(
                sent_at__date=today,
                status='sent'
            ).count()
        else:
            today_messages = TelegramMessage.objects.filter(
                created_by=user,
                sent_at__date=today,
                status='sent'
            ).count()

        return Response({
            'channels': {
                'total': total_channels,
                'active': active_channels
            },
            'messages': {
                'total': total_messages,
                'sent': sent_messages,
                'scheduled': scheduled_messages,
                'failed': failed_messages,
                'today_sent': today_messages
            }
        })

    except Exception as e:
        return Response(
            {'error': f'خطای سیستمی: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )