"""
Utility Selenium reusable (bukan bagian pipeline penelitian):
- pengecekan state browser
- lifecycle driver (init/restart)
- driver.get() dengan retry
- menunggu elemen hasil muncul di DOM

Dipindahkan dari scholar_scraper.py agar file scraping utama lebih ringkas.
Logika dan urutan retry TIDAK diubah, hanya direlokasi + diparameterisasi
supaya reusable (mis. selector kini jadi parameter, bukan hardcode).
"""

import time

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    InvalidSessionIdException,
    WebDriverException,
    TimeoutException,
)
from selenium.webdriver.common.by import By
from urllib.parse import urlparse

from src.utils.driver import setup_driver
from src.utils import logger


def safe_current_url(driver):
    try:
        return driver.current_url
    except Exception:
        return None


def safe_title(driver):
    try:
        return driver.title
    except Exception:
        return None


def is_session_alive(driver):
    if driver is None:
        return False
    try:
        _ = driver.title
        return True
    except (InvalidSessionIdException, WebDriverException):
        return False


def init_driver():
    """Menyiapkan Selenium driver dengan retry sederhana."""
    try:
        return setup_driver(headless=False)
    except Exception as e:
        logger.log_warning(f"⚠ Driver gagal pertama kali: {e}, retry...")
        time.sleep(3)
        return setup_driver(headless=False)


def restart_driver(old_driver, reason=""):
    """Mematikan driver lama (jika ada) dan menyiapkan driver baru."""
    if reason:
        logger.log_retry(f"  ⚠ Restart driver: {reason}")
    if old_driver is not None:
        try:
            old_driver.quit()
        except Exception:
            pass
    time.sleep(3)
    return init_driver()


def log_browser_state(driver, context, keyword=None, page=None, retry=None):
    """Mencetak state browser lengkap agar mudah dilacak kenapa suatu halaman gagal/kosong."""
    current_url = safe_current_url(driver)
    title = safe_title(driver)

    lines = [f"  [STATE] Context      : {context}"]
    if keyword is not None:
        lines.append(f"  [STATE] Keyword      : {keyword}")
    if page is not None:
        lines.append(f"  [STATE] Page         : {page + 1}")
    if retry is not None:
        lines.append(f"  [STATE] Retry ke     : {retry}")
    lines.append(f"  [STATE] Current URL  : {current_url or '-'}")
    lines.append(f"  [STATE] Browser Title: {title or '-'}")

    logger.log_browser(*lines)


def detect_redirect(driver, expected_url):
    """Mendeteksi apakah Google Scholar melakukan redirect di luar dugaan (mis. ke halaman sorry/captcha)."""
    current_url = safe_current_url(driver)
    if not current_url:
        return False
    try:
        expected_host = urlparse(expected_url).netloc
        current_host = urlparse(current_url).netloc
    except Exception:
        return False

    redirected = (current_host != expected_host) or ("/sorry" in current_url)
    if redirected:
        logger.log_warning(
            "  ⚠ [REDIRECT] Terdeteksi redirect ke luar dugaan",
            f"      Expected host : {expected_host}",
            f"      Current URL   : {current_url}",
        )
    return redirected


def safe_driver_get(
    driver,
    url,
    keyword,
    page,
    max_retries,
    backoff_base,
    max_driver_restart,
):
    """
    Melakukan driver.get(url) dengan retry penuh terhadap:
    - WebDriverException / session mati
    - Timeout loading
    - Redirect tidak terduga
    Mengembalikan (driver, success: bool).
    """
    driver_restarts = 0

    for attempt in range(1, max_retries + 1):
        if not is_session_alive(driver):
            if driver_restarts >= max_driver_restart:
                logger.log_error("  ❌ Batas restart driver tercapai, gagal load halaman.")
                return driver, False
            driver = restart_driver(driver, reason="session browser mati sebelum get()")
            driver_restarts += 1

        logger.log_retry(
            f"  [LOAD] URL           : {url}",
            f"  [LOAD] Keyword       : {keyword}",
            f"  [LOAD] Page          : {page + 1}",
            f"  [LOAD] Retry ke      : {attempt}/{max_retries}",
        )

        t0 = time.time()
        try:
            driver.get(url)
            elapsed = time.time() - t0
            logger.log_retry(f"  [LOAD] Loading time  : {elapsed:.2f}s")
            log_browser_state(driver, "Setelah driver.get()", keyword=keyword, page=page, retry=attempt)
            detect_redirect(driver, url)
            return driver, True

        except (InvalidSessionIdException, WebDriverException) as e:
            elapsed = time.time() - t0
            logger.log_warning(f"  ⚠ [LOAD] Gagal get() setelah {elapsed:.2f}s: {e}")
            if driver_restarts >= max_driver_restart:
                logger.log_error("  ❌ Batas restart driver tercapai, gagal load halaman.")
                return driver, False
            driver = restart_driver(driver, reason="WebDriverException saat get()")
            driver_restarts += 1
            time.sleep(backoff_base * attempt)

    return driver, False


def wait_until_results(driver, selector, timeout):
    """Menunggu elemen hasil (berdasarkan selector) selesai dibentuk di DOM, dengan timeout adaptif."""
    try:
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, selector))
        )
        return True
    except TimeoutException:
        return False
    except (InvalidSessionIdException, WebDriverException):
        return False