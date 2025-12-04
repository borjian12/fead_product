from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from .models import CustomUser, SellerProfile, AgentProfile, AdminProfile, BuyerProfile


@receiver(post_save, sender=CustomUser)
def create_user_profile(sender, instance, created, **kwargs):
    """ایجاد پروفایل مربوطه هنگام ایجاد کاربر جدید"""
    if created:
        user_type = instance.user_type

        if user_type == 'seller':
            SellerProfile.objects.create(
                user=instance,
                company_name=instance.company_name or '',
                contact_email=instance.email,
                contact_phone=instance.phone or ''
            )

        elif user_type == 'agent':
            AgentProfile.objects.create(
                user=instance,
                company_name=instance.company_name or '',
                contact_email=instance.email,
                contact_phone=instance.phone or ''
            )

        elif user_type in ['admin', 'super_admin']:
            AdminProfile.objects.create(
                user=instance,
                role=user_type
            )

        elif user_type == 'buyer':
            BuyerProfile.objects.create(user=instance)


@receiver(post_save, sender=CustomUser)
def save_user_profile(sender, instance, **kwargs):
    """ذخیره پروفایل مربوطه"""
    user_type = instance.user_type

    try:
        if user_type == 'seller' and hasattr(instance, 'seller_profile'):
            instance.seller_profile.save()
        elif user_type == 'agent' and hasattr(instance, 'agent_profile'):
            instance.agent_profile.save()
        elif user_type in ['admin', 'super_admin'] and hasattr(instance, 'admin_profile'):
            instance.admin_profile.save()
        elif user_type == 'buyer' and hasattr(instance, 'buyer_profile'):
            instance.buyer_profile.save()
    except Exception as e:
        print(f"Error saving user profile: {e}")


@receiver(pre_save, sender=CustomUser)
def update_profile_info(sender, instance, **kwargs):
    """به‌روزرسانی اطلاعات پروفایل هنگام تغییر اطلاعات کاربر"""
    if not instance.pk:  # اگر کاربر جدید است
        return

    try:
        old_user = CustomUser.objects.get(pk=instance.pk)

        # اگر اطلاعات شرکت تغییر کرده، در پروفایل مربوطه به‌روزرسانی شود
        if old_user.company_name != instance.company_name:
            user_type = instance.user_type

            if user_type == 'seller' and hasattr(instance, 'seller_profile'):
                instance.seller_profile.company_name = instance.company_name

            elif user_type == 'agent' and hasattr(instance, 'agent_profile'):
                instance.agent_profile.company_name = instance.company_name

        # اگر شماره تلفن تغییر کرده
        if old_user.phone != instance.phone:
            user_type = instance.user_type

            if user_type == 'seller' and hasattr(instance, 'seller_profile'):
                instance.seller_profile.contact_phone = instance.phone

            elif user_type == 'agent' and hasattr(instance, 'agent_profile'):
                instance.agent_profile.contact_phone = instance.phone

    except CustomUser.DoesNotExist:
        pass