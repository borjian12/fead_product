# utils/selenium_helper.py
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time


class SeleniumHelper:
    def __init__(self):
        self.driver = None
        # ایجاد مسیر اسکرین‌شات‌ها
        self.screenshots_dir = "/app/screenshots"
        os.makedirs(self.screenshots_dir, exist_ok=True)

    def init_driver(self):
        """ایجاد درایور Selenium"""
        chrome_options = Options()
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        # chrome_options.add_argument('--headless')  # غیرفعال کردن headless برای دیدن در VNC
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')

        # اتصال به Selenium در Docker
        self.driver = webdriver.Remote(
            command_executor='http://selenium:4444/wd/hub',
            options=chrome_options
        )
        return self.driver

    def take_screenshot(self, url, save_path=None):
        """گرفتن اسکرین‌شات از یک URL"""
        try:
            print(f"🌐 Navigating to: {url}")
            self.driver.get(url)

            # منتظر لود شدن صفحه بشو
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )

            # اگر مسیر مشخص نشده، مسیر پیش‌فرض رو استفاده کن
            if save_path is None:
                timestamp = int(time.time())
                save_path = f"{self.screenshots_dir}/screenshot_{timestamp}.png"

            print(f"💾 Saving screenshot to: {save_path}")
            self.driver.save_screenshot(save_path)

            # چک کن که فایل واقعاً ایجاد شده
            if os.path.exists(save_path):
                file_size = os.path.getsize(save_path)
                print(f"✅ Screenshot saved successfully! Size: {file_size} bytes")
                return True
            else:
                print("❌ Screenshot file was not created!")
                return False

        except Exception as e:
            print(f"❌ Error taking screenshot: {e}")
            return False

    def get_page_info(self, url):
        """گرفتن اطلاعات صفحه برای دیباگ"""
        try:
            self.driver.get(url)
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )

            info = {
                'title': self.driver.title,
                'url': self.driver.current_url,
                'page_source_length': len(self.driver.page_source),
                'window_size': self.driver.get_window_size()
            }
            return info
        except Exception as e:
            print(f"❌ Error getting page info: {e}")
            return None

    def close(self):
        """بستن درایور"""
        if self.driver:
            self.driver.quit()