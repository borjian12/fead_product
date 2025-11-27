# auth_app/models.py
from django.db import models
from django.contrib.auth.models import User


class TelegramProfile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='telegram_profile'
    )
    telegram_id = models.BigIntegerField(unique=True)
    language_code = models.CharField(max_length=10, blank=True, null=True)
    is_premium = models.BooleanField(default=False)
    photo_url = models.URLField(max_length=500, blank=True, null=True)

    # فیلدهای جدید
    email = models.EmailField(blank=True, null=True, verbose_name="ایمیل کاربر")
    people = models.TextField(blank=True, null=True,
                              verbose_name="پیپل کاربر")  # یا اگر لیست است، می‌توانید از JSONField استفاده کنید
    amazon_profile_link = models.URLField(max_length=500, blank=True, null=True, verbose_name="لینک پروفایل آمازون")
    amazon_reviews_count = models.IntegerField(default=0, verbose_name="تعداد ریویوهای آمازون")
    amazon_purchases_count = models.IntegerField(default=0, verbose_name="تعداد خریدهای آمازون")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'telegram_profiles'
        verbose_name = 'Telegram Profile'
        verbose_name_plural = 'Telegram Profiles'

    def __str__(self):
        return f"{self.user.username} (ID: {self.telegram_id})"