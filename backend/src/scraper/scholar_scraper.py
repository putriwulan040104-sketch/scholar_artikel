"""
scholar_scraper.py  –  Scraper artikel Google Scholar dengan validasi DOI bertingkat.

Tingkat validasi:
  LEVEL A  →  open_access       : DOI ada + PDF diunduh + pdf_doi ada + cocok dengan doi
  LEVEL B  →  open_access       : DOI ada + PDF diunduh (pdf_doi tidak embed di PDF — umum terjadi)
  LEVEL C  →  closed_access     : DOI ada + tidak ada PDF / PDF tidak bisa diakses

Artikel TANPA DOI sama sekali → skip (tidak disimpan).
Browser Selenium HANYA digunakan untuk browsing Scholar, TIDAK untuk download PDF.
"""

import re
import time
from datetime import datetime, timezone

import requests
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    InvalidSessionIdException,
    WebDriverException,
    NoSuchElementException,
    StaleElementReferenceException,
)

from src.config.supabase_client import supabase
from src.utils.driver import setup_driver, wait_for_captcha_if_needed
from src.utils.delay import human_like_delay
from src.scraper.pdf_handler import download_pdf, extract_doi_from_pdf
from src.scraper.html_parser import normalize_doi, extract_doi_from_scholar_result

# ─── Konstanta ──────────────────────────────────────────────────────────────
TABLE_DOI  = "scholar_article_doi"
YEAR_MIN   = 2021
YEAR_MAX   = 2026
DOI_PATTERN = re.compile(
    r"(?:https?://(?:dx\.)?doi\.org/)?(10\.\d{4,9}/[-._;()/:A-Z0-9]+)",
    re.IGNORECASE,
)

# ─── Helpers ────────────────────────────────────────────────────────────────

def clean_source(rest_text, year):
    """Ekstrak nama jurnal/konferensi dari string metadata Google Scholar."""
    try:
        ym = re.search(r"\b(19|20)\d{2}\b", rest_text)
        if not ym:
            return ""
        before = rest_text[: ym.start()].strip()
        if " - " in before:
            before = before.split(" - ")[0].strip()
        before = re.sub(r"\s+", " ", before).strip(" ,-.")
        bad = ["pdf", "html", "doc", "file", "download"]
        if len(before) < 10 or any(w in before.lower() for w in bad):
            return ""
        return before
    except Exception:
        return ""


def fetch_doi_crossref(title, authors=""):
    """
    Cari DOI via CrossRef API berdasarkan judul.
    Tidak membuka browser — murni HTTP request.
    """
    try:
        params = {"query.title": title, "rows": 1, "select": "DOI,title,score"}
        if authors:
            last = authors.split(",")[0].strip().split()[-1]
            params["query.author"] = last

        r = requests.get(
            "https://api.crossref.org/works",
            params=params,
            timeout=8,
            headers={"User-Agent": "ScholarScraper/2.0 (mailto:research@example.com)"},
        )
        if r.status_code == 200:
            items = r.json().get("message", {}).get("items", [])
            if items and items[0].get("score", 0) >= 30:   # threshold relevansi
                doi = normalize_doi(items[0].get("DOI", ""))
                if doi:
                    print(f"  🔎 CrossRef DOI: {doi}")
                    return doi
    except Exception as e:
        print(f"  ⚠ CrossRef: {e}")
    return None


def fetch_doi_from_doi_org(url):
    """
    Resolve DOI via doi.org/search jika URL artikel mengandung hint DOI.
    Coba ekstrak DOI dari redirect final URL.
    """
    if not url:
        return None
    try:
        # Kadang URL artikel langsung mengandung DOI
        doi = normalize_doi(url)
        if doi:
            return doi
        # Coba ikuti redirect (tanpa render JS) untuk dapat URL final
        r = requests.head(url, allow_redirects=True, timeout=8,
                          headers={"User-Agent": "Mozilla/5.0"})
        final = r.url
        doi = normalize_doi(final)
        if doi:
            print(f"  🌐 DOI dari redirect URL: {doi}")
            return doi
    except Exception:
        pass
    return None


# ─── Duplikasi checks ───────────────────────────────────────────────────────

def _exists(field, value):
    if not value:
        return False
    try:
        res = supabase.table(TABLE_DOI).select("id").eq(field, value).limit(1).execute()
        return bool(res.data)
    except Exception:
        return False

is_doi_dup     = lambda v: _exists("doi", v)
is_url_dup     = lambda v: _exists("url", v)
is_pdfurl_dup  = lambda v: _exists("pdf_url", v)


# ─── Scraper utama ──────────────────────────────────────────────────────────

def _init_driver():
    """Buat driver baru, retry sekali jika gagal."""
    try:
        return setup_driver(headless=False)
    except Exception as e:
        print(f"⚠ Driver gagal pertama kali: {e}, retry...")
        time.sleep(3)
        return setup_driver(headless=False)


def scrape_and_save_to_supabase(keyword, category, max_results=50):
    driver       = None
    success      = 0
    scraped_count = 0
    skipped_total = 0
    page          = 0

    skip_reasons = {
        "judul": 0, "url_dup": 0, "tahun": 0, "source": 0,
        "abstract": 0, "doi": 0, "doi_dup": 0,
        "pdfurl_dup": 0, "disimpan": 0,
    }

    query = keyword.replace(" ", "+")

    try:
        driver = _init_driver()

        while scraped_count < max_results:
            # ── Cek session driver masih hidup ───────────────────────────
            try:
                _ = driver.title  # akan raise jika session mati
            except (InvalidSessionIdException, WebDriverException):
                print("⚠ Session browser mati, restart driver...")
                try:
                    driver.quit()
                except Exception:
                    pass
                time.sleep(3)
                driver = _init_driver()

            start = page * 10
            url   = f"https://scholar.google.com/scholar?q={query}&start={start}"

            print(f"\n{'='*65}")
            print(
                f"📄 Halaman {page+1}  |  "
                f"Valid: {scraped_count}/{max_results}  |  "
                f"Skip: {skipped_total}"
            )
            print(f"{'='*65}")

            try:
                driver.get(url)
            except (InvalidSessionIdException, WebDriverException) as e:
                print(f"⚠ Gagal get URL: {e}, restart driver...")
                try:
                    driver.quit()
                except Exception:
                    pass
                time.sleep(3)
                driver = _init_driver()
                driver.get(url)

            human_like_delay(3, 5)

            if not wait_for_captcha_if_needed(driver):
                print("❌ CAPTCHA tidak selesai, berhenti.")
                break

            try:
                WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, ".gs_r.gs_or.gs_scl")
                    )
                )
            except Exception:
                print("❌ Tidak ada hasil di halaman ini.")
                break

            results = driver.find_elements(By.CSS_SELECTOR, ".gs_r.gs_or.gs_scl")
            if not results:
                print("❌ Tidak ada hasil lagi, scraping selesai.")
                break

            # Snapshot data dari DOM sebelum loop (hindari stale element)
            result_data = []
            for result in results:
                try:
                    rd = {}

                    # Judul & URL
                    title_el = result.find_element(By.CSS_SELECTOR, ".gs_rt")
                    links    = title_el.find_elements(By.TAG_NAME, "a")
                    rd["title"] = (links[0].text.strip() if links
                                   else title_el.text.strip())
                    rd["url"]   = links[0].get_attribute("href") if links else ""

                    # Metadata
                    info   = result.find_element(By.CSS_SELECTOR, ".gs_a").text
                    parts  = info.split(" - ")
                    rd["authors"] = parts[0].strip()
                    rest   = parts[1] if len(parts) > 1 else ""
                    ym     = re.search(r"\b(19|20)\d{2}\b", rest)
                    rd["year"]   = int(ym.group()) if ym else None
                    rd["source"] = clean_source(rest, rd["year"]) if ym else ""

                    # Abstract
                    try:
                        rd["abstract"] = result.find_element(
                            By.CSS_SELECTOR, ".gs_rs").text.strip()
                    except Exception:
                        rd["abstract"] = ""

                    # DOI dari DOM Scholar
                    rd["doi_scholar"] = extract_doi_from_scholar_result(result)

                    # Citations
                    rd["citations"] = 0
                    try:
                        cites = result.find_elements(By.CSS_SELECTOR,
                                                     "a[href*='cites']")
                        if cites:
                            m = re.search(r"\d+", cites[0].text)
                            rd["citations"] = int(m.group()) if m else 0
                    except Exception:
                        pass

                    # PDF URL
                    rd["pdf_url"] = None
                    try:
                        pdf_el = result.find_element(
                            By.CSS_SELECTOR, ".gs_or_ggsm a")
                        rd["pdf_url"] = pdf_el.get_attribute("href") or None
                    except Exception:
                        pass

                    result_data.append(rd)

                except StaleElementReferenceException:
                    continue
                except Exception as e:
                    print(f"  ⚠ Snapshot elemen gagal: {e}")
                    continue

            # ── Proses setiap artikel ─────────────────────────────────────
            for rd in result_data:
                if scraped_count >= max_results:
                    break

                print()

                # 1. Judul
                if not rd.get("title") or len(rd["title"]) < 5:
                    print("⏭  Skip: judul tidak valid")
                    skip_reasons["judul"] += 1
                    skipped_total += 1
                    continue
                print(f"📄 {rd['title'][:72]}")

                # 2. Duplikasi URL
                if is_url_dup(rd.get("url")):
                    print("⏭  Skip: URL sudah ada di DB")
                    skip_reasons["url_dup"] += 1
                    skipped_total += 1
                    continue

                # 3. Tahun
                if not rd.get("year") or not (YEAR_MIN <= rd["year"] <= YEAR_MAX):
                    print(f"⏭  Skip: tahun {rd.get('year')}")
                    skip_reasons["tahun"] += 1
                    skipped_total += 1
                    continue

                # 4. Source
                if not rd.get("source"):
                    print("⏭  Skip: source tidak valid")
                    skip_reasons["source"] += 1
                    skipped_total += 1
                    continue

                # 5. Abstract
                if not rd.get("abstract") or len(rd["abstract"]) < 20:
                    print("⏭  Skip: abstract tidak valid")
                    skip_reasons["abstract"] += 1
                    skipped_total += 1
                    continue

                # 6. Cari DOI artikel (bertingkat)
                doi_article = rd.get("doi_scholar")

                if not doi_article:
                    # Coba dari URL artikel
                    doi_article = fetch_doi_from_doi_org(rd.get("url"))

                if not doi_article:
                    # Fallback CrossRef
                    doi_article = fetch_doi_crossref(rd["title"], rd.get("authors", ""))

                if not doi_article:
                    print("⏭  Skip: DOI tidak ditemukan")
                    skip_reasons["doi"] += 1
                    skipped_total += 1
                    continue

                # 7. Duplikasi DOI
                if is_doi_dup(doi_article):
                    print(f"⏭  Skip: DOI {doi_article} sudah ada di DB")
                    skip_reasons["doi_dup"] += 1
                    skipped_total += 1
                    continue

                # 8. PDF & validasi DOI
                pdf_url  = rd.get("pdf_url")
                pdf_path = None
                pdf_doi  = None
                access   = "closed_access"
                status   = "metadata_only"

                if pdf_url:
                    # Duplikasi PDF URL
                    if is_pdfurl_dup(pdf_url):
                        print("⏭  Skip: PDF URL sudah ada di DB")
                        skip_reasons["pdfurl_dup"] += 1
                        skipped_total += 1
                        continue

                    pdf_path = download_pdf(pdf_url, rd["title"])   # tanpa driver

                    if pdf_path:
                        access = "open_access"
                        status = "pdf_downloaded"
                        pdf_doi = extract_doi_from_pdf(pdf_path)

                        if pdf_doi:
                            # LEVEL A: DOI ada, PDF ada, pdf_doi ada
                            if pdf_doi == doi_article:
                                print(f"  ✅ [LEVEL A] DOI cocok: {doi_article}")
                            else:
                                # DOI beda — tetap simpan, catat ketidakcocokan
                                # (bisa terjadi karena versi preprint vs published)
                                print(
                                    f"  ⚠ [LEVEL A*] DOI berbeda (preprint?):\n"
                                    f"     artikel  : {doi_article}\n"
                                    f"     pdf      : {pdf_doi}\n"
                                    f"     → Simpan dengan doi=artikel, pdf_doi=pdf"
                                )
                        else:
                            # LEVEL B: DOI ada, PDF ada, tapi pdf tidak embed DOI
                            print(f"  ✅ [LEVEL B] PDF ada, pdf_doi tidak embed: {doi_article}")
                    else:
                        status = "pdf_failed"
                        print(f"  ℹ PDF gagal diunduh → closed_access")
                else:
                    print(f"  ℹ Tidak ada PDF → closed_access")

                # LEVEL C: DOI ada, tidak ada PDF (closed_access)
                # → tetap disimpan karena DOI sudah terverifikasi

                # 9. Bangun baris data
                row = {
                    "title":        rd["title"],
                    "authors":      rd.get("authors", ""),
                    "year":         rd["year"],
                    "source":       rd["source"],
                    "abstract":     rd["abstract"],
                    "citations":    rd.get("citations", 0),
                    "url":          rd.get("url", ""),
                    "pdf_url":      pdf_url,
                    "scrape_status": status,
                    "scraped_at":   datetime.now(timezone.utc).isoformat(),
                    "category":     category,
                    "doi":          doi_article,
                    "pdf_doi":      pdf_doi,
                    "access_type":  access,
                }

                scraped_count += 1
                print(
                    f"\n  [{scraped_count}] ✅ ARTIKEL VALID"
                    f"\n  Judul   : {row['title']}"
                    f"\n  DOI     : {row['doi']}"
                    f"\n  Akses   : {row['access_type']}"
                    f"\n  Status  : {row['scrape_status']}"
                )
                print("  " + "-" * 55)

                try:
                    supabase.table(TABLE_DOI).insert(row).execute()
                    success += 1
                    skip_reasons["disimpan"] += 1
                except Exception as e:
                    print(f"  ⚠ Gagal insert Supabase: {e}")
                    scraped_count -= 1  # tidak hitung jika gagal insert

                human_like_delay(1, 3)

            page += 1
            human_like_delay(2, 4)

    except KeyboardInterrupt:
        print("\n⛔ Dihentikan oleh pengguna.")

    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass

        # ── Laporan akhir ─────────────────────────────────────────────────
        print(f"\n{'='*65}")
        print("✅ SELESAI SCRAPING")
        print(f"   Berhasil disimpan  : {success} artikel")
        print(f"   Target             : {max_results} artikel")
        print(f"   Total di-skip      : {skipped_total}")
        print()
        print("  RINCIAN SKIP:")
        labels = {
            "judul":      "Judul tidak valid",
            "url_dup":    "URL duplikat",
            "tahun":      "Tahun di luar range",
            "source":     "Source tidak valid",
            "abstract":   "Abstract tidak valid",
            "doi":        "DOI tidak ditemukan",
            "doi_dup":    "DOI duplikat",
            "pdfurl_dup": "PDF URL duplikat",
        }
        for k, label in labels.items():
            if skip_reasons[k]:
                print(f"    {label:<28}: {skip_reasons[k]}")
        print(f"{'='*65}")