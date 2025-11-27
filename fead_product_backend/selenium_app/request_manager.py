# selenium_app/request_manager.py
import queue
import threading
import uuid
import json
from datetime import datetime
from django.utils import timezone
from selenium.webdriver.support.wait import WebDriverWait

from .models import CrawlRequest
from .driver_manager import SeleniumDriverManager
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By



class SeleniumRequestManager:
    def __init__(self):
        self.driver_manager = SeleniumDriverManager()
        self.worker_threads = {}

    def submit_request(self, driver_name, url, requester, metadata=None):
        """ثبت درخواست جدید"""
        request_id = str(uuid.uuid4())


        # ایجاد رکورد در دیتابیس
        crawl_request = CrawlRequest.objects.create(
            request_id=request_id,
            url=url,
            requester=requester,
            status='QUEUED',
            request_metadata=metadata or {}
        )

        # اضافه کردن به صف درایور
        driver_obj = self.driver_manager.get_or_create_driver(driver_name)
        if driver_obj:
            self.driver_manager.request_queues[driver_name].put({
                'request_id': request_id,
                'url': url,
                'metadata': metadata or {}
            })

            # راه‌اندازی worker اگر وجود نداره
            self._start_worker_if_needed(driver_name)
        else:
            crawl_request.status = 'FAILED'
            crawl_request.error_message = f"Driver {driver_name} not found"
            crawl_request.save()

        return request_id

    def _start_worker_if_needed(self, driver_name):
        """راه‌اندازی worker thread برای درایور"""
        if driver_name not in self.worker_threads or not self.worker_threads[driver_name].is_alive():
            worker = threading.Thread(
                target=self._process_requests,
                args=(driver_name,),
                daemon=True
            )
            self.worker_threads[driver_name] = worker
            worker.start()

    def _process_requests(self, driver_name):
        """پردازش درخواست‌های یک درایور"""
        while True:
            try:
                # دریافت درخواست از صف
                request_data = self.driver_manager.request_queues[driver_name].get(timeout=30)

                with self.driver_manager.driver_locks[driver_name]:
                    self._execute_request(driver_name, request_data)

                self.driver_manager.request_queues[driver_name].task_done()

            except queue.Empty:
                # اگر صف خالی بود، worker رو متوقف کن
                break
            except Exception as e:
                print(f"Error in worker for {driver_name}: {e}")
                continue

    def _execute_request(self, driver_name, request_data):
        """اجرای یک درخواست"""
        request_id = request_data['request_id']
        url = request_data['url']

        try:
            # آپدیت وضعیت در دیتابیس
            crawl_request = CrawlRequest.objects.get(request_id=request_id)
            crawl_request.status = 'PROCESSING'
            crawl_request.started_at = timezone.now()
            crawl_request.save()

            # دریافت درایور
            driver = self.driver_manager.get_or_create_driver(driver_name)

            # اجرای درخواست
            driver.get(url)

            # منتظر لود شدن صفحه
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )

            # گرفتن محتوای صفحه
            html_content = driver.page_source

            # ذخیره نتیجه
            crawl_request.status = 'COMPLETED'
            crawl_request.html_content = html_content
            crawl_request.completed_at = timezone.now()
            crawl_request.save()

            # آپدیت آمار session
            if driver_name in self.driver_manager.driver_sessions:
                self.driver_manager.driver_sessions[driver_name]['request_count'] += 1

        except Exception as e:
            # ذخیره خطا
            crawl_request = CrawlRequest.objects.get(request_id=request_id)
            crawl_request.status = 'FAILED'
            crawl_request.error_message = str(e)
            crawl_request.completed_at = timezone.now()
            crawl_request.save()