from urllib.parse import urlencode
import re

from selenium.webdriver.common.by import By
from selenium.common.exceptions import StaleElementReferenceException

from src.scraper.html_parser import extract_doi_from_scholar_result
from src.scraper.source_selector import choose_pdf_url
from src.utils.delay import human_like_delay
from src.utils.driver import wait_for_captcha_if_needed
from src.utils import helpers
from src.utils import logger


YEAR_MIN = 2021
YEAR_MAX = 2026
SCHOLAR_BASE_URL = "https://scholar.google.co.id/scholar"
SCHOLAR_RESULT_SELECTOR = ".gs_r.gs_or.gs_scl"

# =============================================================================
# KONFIGURASI RETRY & STABILITAS SCRAPER
# (tidak mengubah pipeline penelitian, hanya kestabilan proses Selenium)
# =============================================================================
MAX_DRIVER_RESTART = 6            # batas restart browser sebelum benar-benar menyerah
MAX_PAGE_LOAD_RETRY = 4           # retry driver.get() untuk satu halaman
MAX_EMPTY_RELOAD_RETRY = 4        # retry reload saat DOM/halaman terbaca 0 hasil
RESULT_WAIT_BASE_TIMEOUT = 30     # detik, naik bertahap tiap retry
RESULT_WAIT_TIMEOUT_STEP = 10
PAGE_LOAD_BACKOFF_BASE = 3        # detik, dikali attempt untuk backoff


def build_scholar_search_url(keyword, start):
    """Membuat URL Google Scholar yang konsisten dengan locale Indonesia."""
    params = {
        "start": start,
        "q": keyword,
        "hl": "id",
        "as_sdt": "0,5",
    }
    return f"{SCHOLAR_BASE_URL}?{urlencode(params)}"


def clean_source(rest_text, year):
    """Membersihkan source/publisher dari metadata Google Scholar."""
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


def build_temporary_metadata_row(rd, category):
    """Membuat row raw metadata sementara tanpa DOI final, PDF validation, atau field DB final."""
    return {
        "title":        rd["title"],
        "authors":      rd.get("authors", ""),
        "year":         rd["year"],
        "source":       rd["source"],
        "abstract":     rd["abstract"],
        "url":          rd.get("url", ""),
        "pdf_url":      rd.get("pdf_url"),
        "category":     category,
    }


# =============================================================================
# LOGIKA SCRAPING GOOGLE SCHOLAR (tetap di file ini, bukan utility generik)
# =============================================================================

def _has_next_scholar_page(driver):
    try:
        next_btn = driver.find_element(By.ID, "gs_n")

        links = next_btn.find_elements(By.TAG_NAME, "a")

        for link in links:

            text = (link.text or "").lower()

            aria = (link.get_attribute("aria-label") or "").lower()

            cls = (link.get_attribute("class") or "").lower()

            if (
                "next" in text
                or "berikutnya" in text
                or "next" in aria
                or "berikutnya" in aria
            ):

                if "disabled" in cls:
                    return False

                return True

    except Exception:
        pass

    return False


def _find_scholar_results(driver):
    """Mengambil elemen hasil Google Scholar dengan selector utama."""
    try:
        return driver.find_elements(By.CSS_SELECTOR, SCHOLAR_RESULT_SELECTOR)
    except Exception:
        return []


def _snapshot_scholar_results(results):
    result_data = []
    for result in results:
        try:
            rd = {}
            title_el = result.find_element(By.CSS_SELECTOR, ".gs_rt")
            links = title_el.find_elements(By.TAG_NAME, "a")
            rd["title"] = (links[0].text.strip() if links else title_el.text.strip())
            rd["url"] = links[0].get_attribute("href") if links else ""

            info = result.find_element(By.CSS_SELECTOR, ".gs_a").text
            parts = info.split(" - ")
            rd["authors"] = parts[0].strip()
            rest = parts[1] if len(parts) > 1 else ""
            ym = re.search(r"\b(19|20)\d{2}\b", rest)
            rd["year"] = int(ym.group()) if ym else None
            rd["source"] = clean_source(rest, rd["year"]) if ym else ""

            try:
                rd["abstract"] = result.find_element(By.CSS_SELECTOR, ".gs_rs").text.strip()
            except Exception:
                rd["abstract"] = ""

            rd["doi_scholar"] = extract_doi_from_scholar_result(result)
            rd["pdf_url"] = None
            try:
                pdf_links = result.find_elements(By.CSS_SELECTOR, ".gs_or_ggsm a")
                pdf_urls = [
                    pdf_el.get_attribute("href")
                    for pdf_el in pdf_links
                ]
                rd["pdf_url"] = choose_pdf_url(pdf_urls)
            except Exception:
                pass

            result_data.append(rd)

        except StaleElementReferenceException:
            continue
        except Exception as e:
            logger.log_warning(f"  ⚠ Snapshot elemen gagal: {e}")
            continue

    return result_data


def _resolve_empty_page(driver, url, keyword, page):
    """
    Menangani kasus halaman terbaca 0 hasil padahal browser sebenarnya masih memiliki hasil
    (loading lambat / DOM belum selesai / delay Google Scholar).
    Melakukan reload halaman yang sama beberapa kali sebelum menyimpulkan halaman benar-benar kosong.
    Mengembalikan (driver, results, confirmed_empty: bool).
    """
    for empty_retry in range(1, MAX_EMPTY_RELOAD_RETRY + 1):
        timeout = RESULT_WAIT_BASE_TIMEOUT + (empty_retry - 1) * RESULT_WAIT_TIMEOUT_STEP
        logger.log_retry(
            f"  [EMPTY] Jumlah hasil : 0 (percobaan ke-{empty_retry}/{MAX_EMPTY_RELOAD_RETRY})",
            f"  [EMPTY] Wait timeout : {timeout}s",
        )

        wait_ok = helpers.wait_until_results(driver, SCHOLAR_RESULT_SELECTOR, timeout=timeout)
        results = _find_scholar_results(driver)
        logger.log_retry(f"  [EMPTY] Jumlah hasil setelah wait: {len(results)}")
        helpers.log_browser_state(driver, "Cek ulang hasil kosong", keyword=keyword, page=page, retry=empty_retry)

        if results:
            logger.log_success("  ✅ [EMPTY] Hasil ditemukan setelah retry, halaman TIDAK kosong.")
            return driver, results, False

        if not wait_ok:
            logger.log_warning("  ⚠ [EMPTY] Timeout menunggu DOM hasil.")

        if empty_retry < MAX_EMPTY_RELOAD_RETRY:
            logger.log_retry("  🔄 [EMPTY] Reload halaman yang sama (kemungkinan loading delay Google Scholar)...")
            driver, load_ok = helpers.safe_driver_get(
                driver, url, keyword, page,
                max_retries=MAX_PAGE_LOAD_RETRY,
                backoff_base=PAGE_LOAD_BACKOFF_BASE,
                max_driver_restart=MAX_DRIVER_RESTART,
            )
            if not load_ok:
                logger.log_error("  ❌ [EMPTY] Reload gagal total, hentikan retry halaman kosong.")
                return driver, [], True
            human_like_delay(5, 9)

    logger.log_warning("  ⚠ [EMPTY] Halaman dikonfirmasi kosong setelah seluruh retry.")
    return driver, [], True


def scrape_and_collect_google_scholar(
    keyword,
    category,
    max_results=50,
    start_page=0,
    pages_to_collect=None,
    progress_callback=None,
):
    """Scraping metadata Google Scholar dan mengembalikan temporary dataset tanpa insert database."""
    driver = None
    scraped_count = 0
    skipped_total = 0
    page = start_page
    pages_collected = 0
    has_more_pages = True
    temporary_dataset = []
    driver_restarts = 0

    skip_reasons = {
        "judul": 0, "url_dup": 0, "tahun": 0, "source": 0,
        "abstract": 0, "doi": 0, "doi_dup": 0,
        "pdfurl_dup": 0, "pdf_failed": 0, "metadata_dup": 0,
        "disimpan": 0,
    }

    try:
        driver = helpers.init_driver()

        while max_results is None or scraped_count < max_results:
            if pages_to_collect is not None and pages_collected >= pages_to_collect:
                break

            if not helpers.is_session_alive(driver):
                if driver_restarts >= MAX_DRIVER_RESTART:
                    logger.log_error("❌ Batas restart driver tercapai di awal iterasi, hentikan scraping.")
                    has_more_pages = False
                    break
                logger.log_retry("⚠ Session browser mati, restart driver...")
                driver = helpers.restart_driver(driver, reason="session mati di awal iterasi")
                driver_restarts += 1

            start = page * 10
            url = build_scholar_search_url(keyword, start)
            page_number = page + 1

            if progress_callback:
                progress_callback({
                    "stage": "scrape",
                    "event": "page_start",
                    "page": page_number,
                    "message": f"Sedang memproses halaman {page_number}...",
                    "temporary_count": scraped_count,
                    "skipped_total": skipped_total,
                })

            target_label = max_results if max_results is not None else "FINAL TARGET"
            logger.log_page(
                f"\n{'='*65}",
                f"📄 Halaman {page+1}  |  "
                f"Temporary valid: {scraped_count}/{target_label}  |  "
                f"Skip: {skipped_total}",
                f"{'='*65}",
            )

            driver, load_ok = helpers.safe_driver_get(
                driver, url, keyword, page,
                max_retries=MAX_PAGE_LOAD_RETRY,
                backoff_base=PAGE_LOAD_BACKOFF_BASE,
                max_driver_restart=MAX_DRIVER_RESTART,
            )
            if not load_ok:
                logger.log_error("❌ Gagal memuat halaman setelah seluruh retry, hentikan scraping.")
                has_more_pages = False
                break

            human_like_delay(3, 5)

            if not wait_for_captcha_if_needed(driver):
                logger.log_error("❌ CAPTCHA tidak selesai, berhenti.")
                has_more_pages = False
                break

            helpers.detect_redirect(driver, url)

            # Tunggu hasil muncul (dengan timeout dasar)
            wait_ok = helpers.wait_until_results(driver, SCHOLAR_RESULT_SELECTOR, timeout=RESULT_WAIT_BASE_TIMEOUT)
            results = _find_scholar_results(driver)
            logger.log_retry(f"  [CHECK] Jumlah hasil awal : {len(results)}  (wait_ok={wait_ok})")

            if not results:
                logger.log_warning( f"Halaman {page+1} kosong. Mencoba reload..."
)
                # Bisa jadi false-empty akibat loading lambat / DOM belum selesai / redirect sementara
                driver, results, confirmed_empty = _resolve_empty_page(driver, url, keyword, page)

                if not results and confirmed_empty:
                    if _has_next_scholar_page(driver):
                        logger.log_retry(
                            "➡ Halaman ini benar-benar kosong, tapi Google Scholar masih punya "
                            "halaman berikutnya. Lanjut."
                        )
                        page += 1
                        pages_collected += 1
                        human_like_delay(2, 4)
                        continue
                    logger.log_error("❌ Google Scholar sudah tidak memiliki halaman hasil berikutnya.")
                    has_more_pages = False
                    break

            result_data = _snapshot_scholar_results(results)
            page_valid_start = scraped_count

            for rd in result_data:
                if max_results is not None and scraped_count >= max_results:
                    break

                if not rd.get("title") or len(rd["title"]) < 5:
                    logger.log_skip("\n⏭  Skip: judul tidak valid")
                    skip_reasons["judul"] += 1
                    skipped_total += 1
                    continue
                logger.log_success(f"\n📄 {rd['title'][:72]}")

                if not rd.get("year") or not (YEAR_MIN <= rd["year"] <= YEAR_MAX):
                    logger.log_skip(f"⏭  Skip: tahun {rd.get('year')}")
                    skip_reasons["tahun"] += 1
                    skipped_total += 1
                    continue

                if not rd.get("source"):
                    logger.log_skip("⏭  Skip: source tidak valid")
                    skip_reasons["source"] += 1
                    skipped_total += 1
                    continue

                if not rd.get("abstract") or len(rd["abstract"]) < 20:
                    logger.log_skip("⏭  Skip: abstract tidak valid")
                    skip_reasons["abstract"] += 1
                    skipped_total += 1
                    continue

                row = build_temporary_metadata_row(rd, category)

                scraped_count += 1
                logger.log_success(
                    f"\n  [{scraped_count}] ✅ ARTIKEL VALID"
                    f"\n  Judul   : {row['title']}"
                    f"\n  Source  : {row['source']}"
                    f"\n  Tahun   : {row['year']}",
                    "  " + "-" * 55,
                    "  Data masuk temporary dataset, belum insert database",
                )
                temporary_dataset.append(row)

                human_like_delay(1, 3)

            page_valid_count = scraped_count - page_valid_start
            if progress_callback:
                progress_callback({
                    "stage": "scrape",
                    "event": "page_done",
                    "page": page_number,
                    "found_count": page_valid_count,
                    "message": f"Halaman {page_number} -> ditemukan {page_valid_count} artikel",
                    "temporary_count": scraped_count,
                    "skipped_total": skipped_total,
                    "skip_reasons": skip_reasons.copy(),
                })

            page += 1
            pages_collected += 1
            human_like_delay(15, 25)

        if max_results is not None and scraped_count < max_results and not has_more_pages:
            logger.log_finish(
                f"Target {max_results} artikel tidak tercapai. "
                f"Hanya ditemukan {scraped_count} artikel yang memenuhi seluruh kriteria validasi.",
                "Google Scholar sudah mencapai akhir hasil pencarian.",
            )

    except KeyboardInterrupt:
        logger.log_finish("\n⛔ Dihentikan oleh pengguna.")

    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass

    return (
        temporary_dataset,
        skip_reasons,
        skipped_total,
        scraped_count,
        page,
        has_more_pages,
    )
