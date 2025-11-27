# selenium_app/driver_manager.py
import threading
import queue
import time
import uuid
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import WebDriverException, TimeoutException
from django.utils import timezone
from .models import SeleniumDriver, CrawlRequest, DriverSession


class SeleniumDriverManager:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(SeleniumDriverManager, cls).__new__(cls)
                cls._instance._initialize()
            return cls._instance

    def _initialize(self):
        self.active_drivers = {}  # {driver_name: driver_instance}
        self.driver_locks = {}  # {driver_name: threading.Lock}
        self.request_queues = {}  # {driver_name: queue.Queue}
        self.driver_sessions = {}  # {driver_name: session_data}

    def get_or_create_driver(self, driver_name, driver_type='CHROME', profile_data=None):
        """دریافت یا ایجاد درایور"""
        with self._lock:
            if driver_name in self.active_drivers:
                # چک کردن سلامت درایور موجود
                if self._is_driver_healthy(driver_name):
                    return self.active_drivers[driver_name]
                else:
                    self._cleanup_driver(driver_name)

            # ایجاد درایور جدید
            driver = self._create_driver(driver_type, profile_data)
            self.active_drivers[driver_name] = driver
            self.driver_locks[driver_name] = threading.Lock()
            self.request_queues[driver_name] = queue.Queue()

            # ایجاد session در دیتابیس
            session_id = str(uuid.uuid4())
            driver_obj, created = SeleniumDriver.objects.get_or_create(
                name=driver_name,
                defaults={
                    'driver_type': driver_type,
                    'profile_data': profile_data or {}
                }
            )

            DriverSession.objects.create(
                driver=driver_obj,
                session_id=session_id,
                is_active=True
            )

            self.driver_sessions[driver_name] = {
                'session_id': session_id,
                'created_at': timezone.now(),
                'request_count': 0
            }

            return driver

    def _create_driver(self, driver_type, profile_data):
        """ایجاد درایور Selenium"""
        if driver_type == 'CHROME':
            chrome_options = Options()
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')

            # اعمال تنظیمات پروفایل
            if profile_data:
                if profile_data.get('user_agent'):
                    chrome_options.add_argument(f'--user-agent={profile_data["user_agent"]}')
                if profile_data.get('headless', True):
                    chrome_options.add_argument('--headless')

            driver = webdriver.Remote(
                command_executor='http://selenium:4444/wd/hub',
                options=chrome_options
            )

            # لود کردن کوکی‌ها اگر وجود دارن
            if profile_data and 'cookies' in profile_data:
                driver.get("about:blank")  # برای set cookie نیاز به یک صفحه داریم
                for cookie in profile_data['cookies']:
                    try:
                        driver.add_cookie(cookie)
                    except Exception as e:
                        print(f"Warning: Could not add cookie: {e}")

            return driver

        else:
            raise ValueError(f"Unsupported driver type: {driver_type}")

    def _is_driver_healthy(self, driver_name):
        """بررسی سلامت درایور"""
        try:
            driver = self.active_drivers[driver_name]
            driver.current_url  # یک عملیات ساده برای تست سلامت
            return True
        except WebDriverException:
            return False

    def _cleanup_driver(self, driver_name):
        """پاکسازی درایور مشکل‌دار"""
        try:
            if driver_name in self.active_drivers:
                self.active_drivers[driver_name].quit()
        except:
            pass

        self.active_drivers.pop(driver_name, None)
        self.driver_locks.pop(driver_name, None)
        self.request_queues.pop(driver_name, None)
        self.driver_sessions.pop(driver_name, None)