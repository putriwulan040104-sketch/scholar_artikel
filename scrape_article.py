from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time
import os
import re
import random
from datetime import datetime
from supabase import create_client, Client
from dotenv import load_dotenv
from selenium.webdriver.common.keys import Keys


load_dotenv()

# Konfigurasi Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

TABLE_NAME = "scholar_articles"


def setup_driver(headless=False):
    """Setup Chrome dengan anti-detection untuk bypass reCAPTCHA"""
    options = Options()
    
    if headless:
        options.add_argument("--headless")
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
    options.add_argument("--disable-gpu")
    
    # Window dan display
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--start-maximized")
    
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


def get_citation_formats(driver, result):
    """
    Klik tombol Kutip dan ambil format MLA, APA, dan ISO
    Returns: dict dengan keys 'kutip_mla', 'kutip_apa', 'kutip_iso'
    """
    citations = {
        "kutip_mla": "",
        "kutip_apa": "",
        "kutip_iso": ""
    }
    
    try:
        # Cari tombol kutip di dalam result element
        cite_button = result.find_element(By.CSS_SELECTOR, "a.gs_or_cit.gs_or_btn")
        
        # Klik tombol kutip
        driver.execute_script("arguments[0].click();", cite_button)
        
        # Tunggu popup kutipan muncul
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "gs_citd"))
        )
        
        # Delay kecil untuk memastikan konten dimuat
        time.sleep(0.5)
        
        # Ambil semua baris kutipan
        citation_rows = driver.find_elements(By.CSS_SELECTOR, "#gs_citt table tr")
        
        for row in citation_rows:
            try:
                # Ambil label (MLA, APA, ISO 690)
                label_elem = row.find_element(By.CSS_SELECTOR, "th.gs_cith")
                label = label_elem.text.strip()
                
                # Ambil nilai kutipan
                value_elem = row.find_element(By.CSS_SELECTOR, "td div.gs_citr")
                value = value_elem.text.strip()
                
                # Mapping ke field database
                if label == "MLA":
                    citations["kutip_mla"] = value
                elif label == "APA":
                    citations["kutip_apa"] = value
                elif label.startswith("ISO"):  # "ISO 690"
                    citations["kutip_iso"] = value
                    
            except Exception as e:
                # Skip jika row tidak memiliki format yang diharapkan
                continue
        
        # Tutup popup dengan menekan ESC
        driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
        time.sleep(0.5)
        
    except Exception as e:
        # Jika gagal, coba tutup popup yang mungkin terbuka
        try:
            driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
        except:
            pass
    
    return citations


def scrape_and_save_to_supabase(keyword, max_results=10):
    driver = None
    processed_count = 0
    
    try:
        driver = setup_driver(headless=False)  # HARUS non-headless untuk handle CAPTCHA
        
        query = keyword.replace(" ", "+")
        url = f"https://scholar.google.com/scholar?q={query}&hl=id&as_sdt=0,5"
        
        print(f"Membuka URL: {url}")
        driver.get(url)
        print("Menunggu halaman dimuat...")
        human_like_delay(3, 6)  # Delay natural
        
        # CEK DAN TUNGGU CAPTCHA
        if not wait_for_captcha_if_needed(driver, timeout=300):
            print("Gagal menyelesaikan CAPTCHA. Keluar.")
            return
        
        # Tunggu sampai hasil muncul
        try:
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".gs_r.gs_or.gs_scl"))
            )
            print("✓ Halaman berhasil dimuat!\n")
        except Exception as e:
            print(f"✗ Timeout menunggu hasil: {str(e)}")
            print("Mungkin CAPTCHA masih ada atau halaman error.")
            driver.save_screenshot("error_no_results.png")
            raise
        
        results = driver.find_elements(By.CSS_SELECTOR, ".gs_r.gs_or.gs_scl")
        print(f"Ditemukan {len(results)} hasil artikel")
        print(f"Memproses maksimal {max_results} artikel...\n")
        
        for i, result in enumerate(results[:max_results]):
            try:
                row = {}
                scrape_status = "success"
                
                print(f"[{i+1}/{max_results}] Memproses artikel...")
                
                # Judul & URL
                try:
                    title_elem = result.find_element(By.CSS_SELECTOR, ".gs_rt a")
                    row["title"] = title_elem.text.strip()
                    row["url"] = title_elem.get_attribute("href") or ""
                    print(f"  📄 {row['title'][:60]}...")
                except Exception as e:
                    row["title"] = "[tidak ditemukan]"
                    row["url"] = ""
                    scrape_status = "failed"
                    print(f"  ✗ Error ambil judul")
                
                # Authors, Year, Source
                try:
                    info_text = result.find_element(By.CSS_SELECTOR, ".gs_a").text.strip()
                    if " - " in info_text:
                        authors_part, rest = info_text.split(" - ", 1)
                        row["authors"] = authors_part.strip()
                    else:
                        row["authors"] = info_text.strip()
                        rest = ""
                    
                    year_match = re.search(r'\b(\d{4})\b', rest)
                    row["year"] = int(year_match.group(1)) if year_match else None
                    
                    if row["year"]:
                        source_parts = rest.split(str(row["year"]), 1)
                        row["source"] = (source_parts[1].strip(" -,").strip() if len(source_parts) > 1 else source_parts[0].strip())
                    else:
                        row["source"] = rest.strip()
                    
                    print(f"  👤 {row['authors'][:40]}... ({row['year']})")
                except Exception as e:
                    row["authors"] = ""
                    row["year"] = None
                    row["source"] = ""
                    scrape_status = "failed"
                
                # Abstract
                try:
                    row["abstract"] = result.find_element(By.CSS_SELECTOR, ".gs_rs").text.strip()
                    print(f"  📝 Abstract: {len(row['abstract'])} chars")
                except:
                    row["abstract"] = ""
                
                # Citations
                try:
                    citation_links = result.find_elements(By.CSS_SELECTOR, "div.gs_fl a[href*='cites=']")
                    if citation_links:
                        citation_text = citation_links[0].text
                        match = re.search(r'(\d+)', citation_text)
                        row["citations"] = int(match.group(1)) if match else 0
                    else:
                        row["citations"] = 0
                    print(f"  📊 Citations: {row['citations']}")
                except:
                    row["citations"] = 0
                
                # ===================================
                # KUTIPAN (MLA, APA, ISO)
                # ===================================
                print("  📋 Mengambil format kutipan...")
                citation_formats = get_citation_formats(driver, result)
                row["kutip_mla"] = citation_formats["kutip_mla"]
                row["kutip_apa"] = citation_formats["kutip_apa"]
                row["kutip_iso"] = citation_formats["kutip_iso"]
                
                if row["kutip_mla"]:
                    print(f"     ✓ MLA: {row['kutip_mla'][:50]}...")
                if row["kutip_apa"]:
                    print(f"     ✓ APA: {row['kutip_apa'][:50]}...")
                if row["kutip_iso"]:
                    print(f"     ✓ ISO: {row['kutip_iso'][:50]}...")
                
                if not any([row["kutip_mla"], row["kutip_apa"], row["kutip_iso"]]):
                    print("     ⚠ Tidak ada kutipan yang ditemukan")
                
                # Metadata
                now_timestamp = datetime.now().isoformat()
                row["scraped_at"] = now_timestamp
                row["scrape_status"] = scrape_status
                
                # Simpan ke Supabase
                print("  💾 Menyimpan ke database...")
                check_response = supabase.table(TABLE_NAME).select("id").eq("title", row["title"]).execute()
                
                if check_response.data:
                    # UPDATE existing
                    article_id = check_response.data[0]["id"]
                    update_response = supabase.table(TABLE_NAME).update({
                        "title": row["title"],
                        "abstract": row["abstract"],
                        "authors": row["authors"],
                        "source": row["source"],
                        "year": row["year"],
                        "citations": row["citations"],
                        "url": row["url"],
                        "kutip_mla": row["kutip_mla"],
                        "kutip_apa": row["kutip_apa"],
                        "kutip_iso": row["kutip_iso"],
                        "scraped_at": row["scraped_at"],
                        "scrape_status": row["scrape_status"],
                    }).eq("id", article_id).execute()
                    
                    if update_response.data:
                        processed_count += 1
                        print("  ✓ UPDATE berhasil\n")
                    else:
                        print("  ✗ UPDATE gagal\n")
                else:
                    # INSERT new
                    insert_response = supabase.table(TABLE_NAME).insert({
                        "title": row["title"],
                        "abstract": row["abstract"],
                        "authors": row["authors"],
                        "source": row["source"],
                        "year": row["year"],
                        "citations": row["citations"],
                        "url": row["url"],
                        "kutip_mla": row["kutip_mla"],
                        "kutip_apa": row["kutip_apa"],
                        "kutip_iso": row["kutip_iso"],
                        "scraped_at": row["scraped_at"],
                        "scrape_status": row["scrape_status"],
                    }).execute()
                    
                    if insert_response.data:
                        processed_count += 1
                        print("  ✓ INSERT berhasil\n")
                    else:
                        print("  ✗ INSERT gagal\n")
                
                # Delay natural antar artikel
                human_like_delay(2, 4)
                
            except Exception as e:
                print(f"  ✗ Error: {str(e)}\n")
                continue
    
    except Exception as e:
        print(f"\n✗ ERROR: {str(e)}\n")
        import traceback
        traceback.print_exc()
    
    finally:
        if driver:
            print("\n" + "="*60)
            input("Tekan ENTER untuk menutup browser dan selesai...")
            driver.quit()
    
    print(f"\n{'='*60}")
    print(f"✓ SELESAI!")
    print(f"Berhasil: {processed_count}/{max_results} artikel")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    print("="*60)
    print("GOOGLE SCHOLAR SCRAPER - WITH CITATIONS")
    print("="*60)
    print("\n📌 FITUR:")
    print("- Scrape artikel dari Google Scholar")
    print("- Ambil format kutipan: MLA, APA, ISO 690")
    print("- Anti-CAPTCHA detection")
    print("- Simpan ke Supabase")
    print("\n⚠ PENTING:")
    print("- Chrome window AKAN TERLIHAT (diperlukan untuk CAPTCHA)")
    print("- Jika muncul CAPTCHA, selesaikan di browser")
    print("- Script akan menunggu hingga CAPTCHA selesai")
    print("- Gunakan dengan bijak, jangan spam request\n")
    
    keyword = input("Masukkan kata kunci: ").strip() or "machine learning indonesia"
    print(f"\n🔍 Kata kunci: '{keyword}'")
    print("Memulai scraping...\n")
    
    scrape_and_save_to_supabase(keyword, max_results=10)