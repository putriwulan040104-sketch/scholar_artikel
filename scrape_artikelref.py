from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

import os
import re
import time
import random
import requests
import pdfplumber
from PyPDF2 import PdfReader
from datetime import datetime
from urllib.parse import urlparse

from supabase import create_client, Client
from dotenv import load_dotenv

# =========================
# ENV & DATABASE
# =========================
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
TABLE_NAME = "scholar_articles_refs"

# =========================
# DRIVER
# =========================
def setup_driver():
    options = Options()
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--remote-debugging-port=9222")
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-software-rasterizer")

    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/121.0.0.0 Safari/537.36",
    ]
    options.add_argument(f"user-agent={random.choice(user_agents)}")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {
            "source": """
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'languages', {get: () => ['id-ID','en-US']});
            Object.defineProperty(navigator, 'plugins', {get: () => [1,2,3]});
            """
        },
    )
    driver.implicitly_wait(10)
    return driver

def human_delay(a=2, b=4):
    time.sleep(random.uniform(a, b))

# =========================
# PDF & REFERENCES
# =========================
def download_pdf(url, folder="pdfs"):
    os.makedirs(folder, exist_ok=True)
    filename = os.path.join(folder, os.path.basename(urlparse(url).path))
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        if not url.lower().endswith(".pdf"):
            return None  # skip kalau link bukan PDF

        r = requests.get(url, headers=headers, timeout=20)
        r.raise_for_status()
        if "forbidden" in r.text.lower() or r.status_code == 403:
            return None
        with open(filename, "wb") as f:
            f.write(r.content)
        return filename
    except requests.exceptions.RequestException:
        return None

def is_pdf_valid(pdf_path):
    try:
        PdfReader(pdf_path)
        return True
    except:
        return False

def extract_references_from_pdf(pdf_path):
    """
    Extract references/bibliography from PDF even if no 'References' title.
    Detect lines that look like citation entries (contain year + comma, URL, or (Name, Year)).
    """
    references = ""
    if not is_pdf_valid(pdf_path):
        print("⚠ PDF invalid / corrupted")
        return references

    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if not text:
                    continue
                lines = text.split("\n")
                for line in lines:
                    # regex: tahun + koma atau ada URL atau (Nama, Tahun)
                    if re.search(r"\b\d{4}\b", line) and ("," in line or "http" in line or re.search(r"\(.+,\s*\d{4}\)", line)):
                        references += line.strip() + "\n"
    except Exception as e:
        print(f"⚠ Error parsing PDF: {e}")
    return references.strip()

def extract_references_from_html(driver):
    """
    Fallback jika PDF gagal, coba ambil references dari halaman HTML
    """
    refs = ""
    try:
        page_text = driver.page_source
        lines = page_text.split("\n")
        for line in lines:
            if re.search(r"\b\d{4}\b", line) and ("," in line or "http" in line or re.search(r"\(.+,\s*\d{4}\)", line)):
                refs += line.strip() + "\n"
    except:
        pass
    return refs.strip()

# =========================
# SCRAPER
# =========================
def scrape_scholar(keyword, max_results=10):
    driver = setup_driver()
    query = keyword.replace(" ", "+")
    url = f"https://scholar.google.com/scholar?q={query}&hl=id"

    driver.get(url)
    human_delay(4, 6)

    WebDriverWait(driver, 30).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, ".gs_r.gs_or.gs_scl"))
    )
    results = driver.find_elements(By.CSS_SELECTOR, ".gs_r.gs_or.gs_scl")

    for i, result in enumerate(results[:max_results]):
        print(f"\n[{i+1}] Scraping artikel")

        data = {
            "title": "",
            "authors": "",
            "year": None,
            "source": "",
            "url": "",
            "pdf_url": "",
            "citations": 0,
            "references_text": "",
            "references_status": "",
            "scraped_at": datetime.now().isoformat(),
        }

        # ambil judul & halaman artikel
        try:
            title_el = result.find_element(By.CSS_SELECTOR, ".gs_rt a")
            data["title"] = title_el.text.strip()
            data["url"] = title_el.get_attribute("href")
            print("📄", data["title"][:80])
        except:
            continue

        # ambil author & year
        try:
            info = result.find_element(By.CSS_SELECTOR, ".gs_a").text
            data["authors"] = info.split("-")[0].strip()
            year = re.search(r"\b\d{4}\b", info)
            data["year"] = int(year.group()) if year else None
            data["source"] = info
        except:
            pass

        # ambil jumlah citation
        try:
            cite = result.find_element(By.CSS_SELECTOR, "a[href*='cites']")
            data["citations"] = int(re.search(r"\d+", cite.text).group())
        except:
            data["citations"] = 0

        # ambil link PDF free di kanan
        pdf_url = ""
        try:
            pdf_link_el = result.find_element(By.CSS_SELECTOR, ".gs_or_ggsm a")
            pdf_url = pdf_link_el.get_attribute("href")
        except:
            pdf_url = None

        data["pdf_url"] = pdf_url
        if pdf_url:
            print("PDF URL:", pdf_url)
            pdf_path = download_pdf(pdf_url)
            if pdf_path:
                refs = extract_references_from_pdf(pdf_path)
                if refs:
                    data["references_text"] = refs
                    data["references_status"] = "PDF success"
                    print(f"📚 References chars (PDF): {len(refs)}")
                else:
                    # fallback ke HTML jika PDF valid tapi references kosong
                    driver.get(data["url"])
                    human_delay(2,3)
                    refs_html = extract_references_from_html(driver)
                    data["references_text"] = refs_html
                    data["references_status"] = "HTML fallback" if refs_html else "PDF empty"
                    print(f"📚 References chars (HTML fallback): {len(refs_html)}")
            else:
                data["references_text"] = ""
                data["references_status"] = "PDF fail / maybe paid or redirect"
                print("⚠ Gagal download PDF, references dikosongkan")
        else:
            # fallback ke HTML jika PDF tidak ada
            driver.get(data["url"])
            human_delay(2,3)
            refs_html = extract_references_from_html(driver)
            data["references_text"] = refs_html
            data["references_status"] = "HTML fallback" if refs_html else "No PDF / metadata only"
            print(f"📚 References chars (HTML fallback): {len(refs_html)}")

        # Simpan ke database
        try:
            supabase.table(TABLE_NAME).insert(data).execute()
            print("💾 Simpan ke database")
        except Exception as e:
            print(f"⚠ Gagal simpan ke database: {e}")

        human_delay(2, 4)

    input("\nTekan ENTER untuk selesai...")
    driver.quit()


# =========================
# RUN
# =========================
if __name__ == "__main__":
    print("=" * 60)
    print("FINAL SCRAPER - PDF + HTML FALLBACK REFERENCES")
    print("=" * 60)

    keyword = input("Masukkan kata kunci: ").strip()
    scrape_scholar(keyword, max_results=10)
