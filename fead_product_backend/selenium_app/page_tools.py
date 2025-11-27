# selenium_app/page_tools.py
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException


class PageTools:
    def __init__(self, driver):
        self.driver = driver
        self.wait = WebDriverWait(driver, 10)

    def find_element(self, selector, by=By.CSS_SELECTOR, timeout=10):
        """پیدا کردن المنت با wait"""
        try:
            wait = WebDriverWait(self.driver, timeout)
            element = wait.until(EC.presence_of_element_located((by, selector)))
            return element
        except TimeoutException:
            raise NoSuchElementException(f"Element not found: {selector}")

    def find_elements(self, selector, by=By.CSS_SELECTOR, timeout=10):
        """پیدا کردن چندین المنت"""
        try:
            wait = WebDriverWait(self.driver, timeout)
            elements = wait.until(EC.presence_of_all_elements_located((by, selector)))
            return elements
        except TimeoutException:
            return []

    def click_element(self, selector, by=By.CSS_SELECTOR):
        """کلیک روی المنت"""
        element = self.find_element(selector, by)
        element.click()

    def type_text(self, selector, text, by=By.CSS_SELECTOR):
        """تایپ متن در فیلد"""
        element = self.find_element(selector, by)
        element.clear()
        element.send_keys(text)

    def get_attribute(self, selector, attribute, by=By.CSS_SELECTOR):
        """گرفتن attribute از المنت"""
        element = self.find_element(selector, by)
        return element.get_attribute(attribute)

    def execute_script(self, script, *args):
        """اجرای JavaScript"""
        return self.driver.execute_script(script, *args)

    def take_screenshot(self, save_path):
        """گرفتن اسکرین‌شات"""
        self.driver.save_screenshot(save_path)

    def get_cookies(self):
        """گرفتن تمام کوکی‌ها"""
        return self.driver.get_cookies()

    def add_cookies(self, cookies):
        """اضافه کردن کوکی‌ها"""
        for cookie in cookies:
            self.driver.add_cookie(cookie)