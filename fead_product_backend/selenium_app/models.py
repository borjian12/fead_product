# selenium_app/models.py
from django.db import models
from django.utils import timezone


class SeleniumDriver(models.Model):
    DRIVER_TYPES = [
        ('CHROME', 'Chrome'),
        ('FIREFOX', 'Firefox'),
        ('EDGE', 'Edge'),
    ]

    name = models.CharField(max_length=100, unique=True)
    driver_type = models.CharField(max_length=10, choices=DRIVER_TYPES, default='CHROME')
    profile_data = models.JSONField(default=dict, blank=True)  # برای ذخیره پروفایل/کوکی‌ها
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.driver_type})"


class CrawlRequest(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PROCESSING', 'Processing'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
        ('QUEUED', 'Queued'),
    ]

    driver = models.ForeignKey(SeleniumDriver, on_delete=models.CASCADE, related_name='requests',null=True, blank=True)
    request_id = models.CharField(max_length=100, unique=True)
    url = models.URLField(max_length=500)
    requester = models.CharField(max_length=100, null=True, blank=True)  # شناسه درخواست‌دهنده
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    html_content = models.TextField(blank=True)
    error_message = models.TextField(blank=True)
    request_metadata = models.JSONField(default=dict, blank=True)  # metadata اضافی
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['request_id']),
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.request_id} - {self.url}"


class DriverSession(models.Model):
    driver = models.ForeignKey(SeleniumDriver, on_delete=models.CASCADE, related_name='sessions')
    session_id = models.CharField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Session {self.session_id} for {self.driver.name}"