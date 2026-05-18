import os
import re
import time
import random
# from unicodedata import category
import requests
import pdfplumber
from PyPDF2 import PdfReader
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client, Client

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# =========================================================
# ENV & SUPABASE
# =========================================================
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

TABLE_NAME = "scholar_articles"

PDF_DIR = "pdfs"
os.makedirs(PDF_DIR, exist_ok=True)

# =========================================================
# SETUP DRIVER (ANTI CAPTCHA)
# =========================================================
def setup_driver(headless=False):
    """Setup Chrome dengan anti-detection untuk bypass reCAPTCHA"""
    options = Options()
    
    if headless:
        options.add_argument("--headless=new")
        print("⚠ Mode: HEADLESS")
    else:
        print("ℹ Mode: NORMAL (Chrome window terlihat)")
    
    # ANTI-DETECTION: Opsi penting untuk terlihat seperti browser normal
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    # Stability options
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    #options.add_argument("--disable-gpu")#
    
    # Window dan display
    options.add_argument("--window-size=1920,1080")
    #options.add_argument("--start-maximized")
    
    # User agent yang lebih natural
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    ]
    options.add_argument(f"user-agent={random.choice(user_agents)}")
    
    # Preferences untuk terlihat lebih natural
    prefs = {
        "profile.default_content_setting_values.notifications": 2,
        "profile.default_content_settings.popups": 0,
        "credentials_enable_service": False,
        "profile.password_manager_enabled": False,
    }
    options.add_experimental_option("prefs", prefs)
    
    # Log level
    options.add_argument("--log-level=3")
    
    try:
        print("Membuat Chrome driver dengan anti-detection...")
        service = Service(ChromeDriverManager().install())
        
        import platform
        if platform.system() == "Windows":
            service.log_path = "NUL"
        
        driver = webdriver.Chrome(service=service, options=options)
        
        # PENTING: Inject script untuk hide webdriver property
        driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': '''
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                
                // Override navigator properties
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });
                
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en', 'id']
                });
                
                // Chrome runtime
                window.chrome = {
                    runtime: {}
                };
                
                // Permissions
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                        Promise.resolve({ state: Notification.permission }) :
                        originalQuery(parameters)
                );
            '''
        })
        
        driver.set_page_load_timeout(60)
        driver.implicitly_wait(10)
        
        print("✓ Chrome driver berhasil dibuat dengan anti-detection!\n")
        return driver
        
    except Exception as e:
        print(f"✗ Error membuat Chrome driver: {str(e)}\n")
        raise


def wait_for_captcha_if_needed(driver, timeout=300):
    """Tunggu user menyelesaikan CAPTCHA jika muncul"""
    try:
        # Cek apakah ada reCAPTCHA
        captcha_elements = driver.find_elements(By.CSS_SELECTOR, "iframe[src*='recaptcha']")
        
        if captcha_elements:
            print("\n" + "="*60)
            print("⚠ RECAPTCHA TERDETEKSI!")
            print("="*60)
            print("Silakan selesaikan CAPTCHA di browser Chrome yang terbuka.")
            print("Script akan menunggu hingga CAPTCHA selesai...")
            print(f"Timeout: {timeout} detik")
            print("="*60 + "\n")
            
            start_time = time.time()
            while time.time() - start_time < timeout:
                # Cek apakah CAPTCHA sudah hilang
                captcha_still_there = driver.find_elements(By.CSS_SELECTOR, "iframe[src*='recaptcha']")
                
                # Atau cek apakah hasil scholar sudah muncul
                results = driver.find_elements(By.CSS_SELECTOR, ".gs_r.gs_or.gs_scl")
                
                if not captcha_still_there or results:
                    print("✓ CAPTCHA selesai atau tidak ada lagi!\n")
                    return True
                
                time.sleep(2)
            
            print("✗ Timeout menunggu CAPTCHA diselesaikan.\n")
            return False
        
        return True  # Tidak ada CAPTCHA
        
    except Exception as e:
        print(f"Error saat cek CAPTCHA: {str(e)}")
        return True


def human_like_delay(min_sec=2, max_sec=5):
    """Delay random untuk terlihat seperti manusia"""
    delay = random.uniform(min_sec, max_sec)
    time.sleep(delay)

# =========================================================
# PDF DOWNLOAD (REQUESTS)
# =========================================================
def download_pdf(pdf_url, title):
    try:
        safe_title = re.sub(r"[^\w]+", "_", title)[:80]
        file_path = os.path.join(PDF_DIR, f"{safe_title}.pdf")

        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(pdf_url, headers=headers, timeout=30, allow_redirects=True)

        if (
            r.status_code == 200
            and ("application/pdf" in r.headers.get("Content-Type", "").lower()
                or r.content[:4] == b"%PDF")
        ):
            with open(file_path, "wb") as f:
                f.write(r.content)
            print("✓ PDF berhasil di-download")
            return file_path

        print("⚠ File bukan PDF valid")
        return None

    except Exception as e:
        print(f"✗ Gagal download PDF: {e}")
        return None
    
def is_pdf_valid(pdf_path):
    try:
        PdfReader(pdf_path)
        return True
    except:
        return False

def extract_references_from_pdf(pdf_path):
    references = ""

    if not is_pdf_valid(pdf_path):
        print("⚠ PDF tidak valid")
        return references

    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if not text:
                    continue

                lines = text.split("\n")
                for line in lines:
                    if re.search(r"\b\d{4}\b", line) and (
                        "," in line or "http" in line or re.search(r"\(.+,\s*\d{4}\)", line)
                    ):
                        references += line.strip() + "\n"

    except Exception as e:
        print(f"⚠ Error parsing PDF: {e}")

    return references.strip()


def extract_references_from_html(driver):
    refs = ""
    try:
        page_text = driver.page_source
        lines = page_text.split("\n")

        for line in lines:
            if re.search(r"\b\d{4}\b", line) and (
                "," in line or "http" in line or re.search(r"\(.+,\s*\d{4}\)", line)
            ):
                refs += line.strip() + "\n"
    except:
        pass

    return refs.strip()

# =========================================================
# SCRAPER + LOGIKA BARU
# =========================================================

def scrape_and_save_to_supabase(keyword, category, max_results=50):
    driver = None
    success = 0
    scraped_count = 0

    try:
        driver = setup_driver(headless=False)

        query = keyword.replace(" ", "+")
        results_per_page = 10
        total_pages = (max_results // results_per_page) + 1

        for page in range(total_pages):
            start = page * results_per_page
            url = f"https://scholar.google.com/scholar?q={query}&hl=id&as_sdt=0,5&start={start}"

            print(f"\n📄 Membuka halaman {page + 1}")
            print(f"URL: {url}")

            driver.get(url)
            human_like_delay(4, 7)

            if not wait_for_captcha_if_needed(driver, timeout=300):
                print("❌ CAPTCHA gagal, scraping dihentikan.")
                break

            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".gs_r.gs_or.gs_scl"))
            )

            results = driver.find_elements(By.CSS_SELECTOR, ".gs_r.gs_or.gs_scl")
            print(f"Ditemukan {len(results)} artikel di halaman ini")


            # =========================
            # LOOP ARTIKEL
            # =========================
            for result in results:
                if scraped_count >= max_results:
                    break

                scraped_count += 1
                print(f"\n[{scraped_count}] Memproses artikel")

                row = {
                    "title": "",
                    "authors": "",
                    "year": None,
                    "source": "",
                    "abstract": "",
                    "citations": 0,
                    "url": "",
                    "pdf_url": None,
                    "references_text": "",
                    "references_status": "",
                    "scrape_status": "metadata_only",
                    "scraped_at": datetime.now().isoformat(),
                    "category": category,
                }

                # =========================
                # TITLE & URL
                # =========================
                try:
                    title_el = result.find_element(By.CSS_SELECTOR, ".gs_rt")
                    link_el = title_el.find_elements(By.TAG_NAME, "a")

                    if link_el:
                        row["title"] = link_el[0].text.strip()
                        row["url"] = link_el[0].get_attribute("href")
                    else:
                        row["title"] = title_el.text.strip()
                        row["url"] = None

                    if not row["title"]:
                        print("❌ Judul kosong")
                        continue

                    print("📄", row["title"][:80])

                except Exception as e:
                    print("❌ Gagal ambil judul:", e)
                    continue

                # =========================
                # DUPLICATE CHECK
                # =========================
                existing = supabase.table(TABLE_NAME).select("id").eq("url", row["url"]).execute()
                if existing.data:
                    print("⚠ Artikel sudah ada, dilewati")
                    continue

                # =========================
                # AUTHORS, YEAR, SOURCE
                # =========================
                try:
                    info_text = result.find_element(By.CSS_SELECTOR, ".gs_a").text.strip()

                    if " - " in info_text:
                        authors_part, rest = info_text.split(" - ", 1)
                    else:
                        authors_part = info_text
                        rest = ""

                    row["authors"] = authors_part.strip()

                    year_match = re.search(r"\b(19|20)\d{2}\b", rest)
                    row["year"] = int(year_match.group()) if year_match else None

                    # FILTER TAHUN 2021 - 2026
                    if row["year"] is None or not (2021 <= row["year"] <= 2026):
                        print(f"⏭ Skip (tahun tidak sesuai): {row['year']}")
                        continue

                    # Ambil source setelah tahun
                    source_part = rest.split(str(row["year"]), 1)[-1]
                    row["source"] = source_part.strip(" ,-.")

                except:
                    pass

                # =========================
                # ABSTRACT
                # =========================
                try:
                    row["abstract"] = result.find_element(By.CSS_SELECTOR, ".gs_rs").text.strip()
                except:
                    row["abstract"] = ""

                # =========================
                # CITATIONS
                # =========================
                try:
                    cite_links = result.find_elements(By.CSS_SELECTOR, "a[href*='cites=']")
                    if cite_links:
                        match = re.search(r"\d+", cite_links[0].text)
                        row["citations"] = int(match.group()) if match else 0
                except:
                    row["citations"] = 0

                # =========================
                # PDF + REFERENCES
                # =========================
                try:
                    pdf_el = result.find_element(By.CSS_SELECTOR, ".gs_or_ggsm a")
                    pdf_url = pdf_el.get_attribute("href")
                    row["pdf_url"] = pdf_url

                    print("📥 PDF ditemukan")

                    pdf_path = download_pdf(pdf_url, row["title"])

                    if pdf_path:
                        row["scrape_status"] = "pdf_downloaded"

                        refs = extract_references_from_pdf(pdf_path)

                        if refs:
                            row["references_text"] = refs
                            row["references_status"] = "PDF success"
                            print(f"📚 References (PDF): {len(refs)} chars")
                        else:
                            print("⚠ PDF tidak ada references → fallback HTML")

                            driver.get(row["url"])
                            human_like_delay(2, 3)

                            refs_html = extract_references_from_html(driver)
                            row["references_text"] = refs_html
                            row["references_status"] = "HTML fallback" if refs_html else "PDF empty"

                    else:
                        row["scrape_status"] = "pdf_url_only"

                        print("⚠ PDF gagal → fallback HTML")

                        driver.get(row["url"])
                        human_like_delay(2, 3)

                        refs_html = extract_references_from_html(driver)
                        row["references_text"] = refs_html
                        row["references_status"] = "HTML fallback" if refs_html else "No PDF"

                except Exception as e:
                    print(f"⚠ Tidak ada PDF / error: {e}")

                    row["pdf_url"] = None
                    row["scrape_status"] = "no_pdf"

                    driver.get(row["url"])
                    human_like_delay(2, 3)

                    refs_html = extract_references_from_html(driver)
                    row["references_text"] = refs_html
                    row["references_status"] = "HTML only" if refs_html else "No references"

                # =========================
                # INSERT SUPABASE
                # =========================
                insert = supabase.table(TABLE_NAME).insert(row).execute()

                if insert.data:
                    success += 1
                    print("✅ Data disimpan")

                time.sleep(random.uniform(2, 4))

    finally:
        if driver:
            driver.quit()

        print("\n" + "=" * 60)
        print(f"SELESAI — berhasil {success}/{max_results}")
        print("=" * 60)


# =========================================================
# MAIN
# =========================================================
if __name__ == "__main__":
    print("=" * 60)
    print("GOOGLE SCHOLAR SCRAPER — FINAL TERPADU")
    print("=" * 60)
    print("- Anti CAPTCHA")
    print("- Download PDF (open-access)")
    print("- Metadata only jika berbayar")
    print("- Supabase storage\n")

    keyword = input("Masukkan kata kunci: ").strip()
    # otomatis keyword jadi category
    category = keyword 
    scrape_and_save_to_supabase(keyword, category, max_results=50)

