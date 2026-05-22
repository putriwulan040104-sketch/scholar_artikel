import random
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By

def setup_driver(headless=False):
    options = Options()

    if headless:
        options.add_argument("--headless=new")

    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)

    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")

    user_agents = [
        "Mozilla/5.0 ... Chrome/120",
        "Mozilla/5.0 ... Chrome/119",
    ]
    options.add_argument(f"user-agent={random.choice(user_agents)}")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    driver.set_page_load_timeout(60)
    driver.implicitly_wait(10)

    return driver


def wait_for_captcha_if_needed(driver, timeout=300):
    start = time.time()
    while time.time() - start < timeout:
        captcha = driver.find_elements(By.CSS_SELECTOR, "iframe[src*='recaptcha']")
        results = driver.find_elements(By.CSS_SELECTOR, ".gs_r.gs_or.gs_scl")

        if not captcha or results:
            return True

        time.sleep(2)

    return False