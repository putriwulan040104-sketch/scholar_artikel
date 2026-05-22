from datetime import datetime
import re

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from src.config.supabase_client import supabase
from src.config.settings import TABLE_NAME

from src.utils.driver import setup_driver, wait_for_captcha_if_needed
from src.utils.delay import human_like_delay

from src.scraper.pdf_handler import download_pdf


def clean_source(rest_text, year):
    """🔥 Extract source lebih akurat (anti 'empathy')"""
    try:
        year_match = re.search(r"\b(19|20)\d{2}\b", rest_text)
        if not year_match:
            return ""

        before_year = rest_text[:year_match.start()].strip()

        # buang publisher (setelah "-")
        if " - " in before_year:
            before_year = before_year.split(" - ")[0].strip()

        # normalize spasi
        before_year = re.sub(r"\s+", " ", before_year).strip(" ,-.")

        # filter kata jelek
        bad_words = ["pdf", "html", "doc", "file", "download"]

        if (
            len(before_year) < 10
            or any(word in before_year.lower() for word in bad_words)
        ):
            return ""

        return before_year

    except:
        return ""


def scrape_and_save_to_supabase(keyword, category, max_results=50):
    driver = None
    success = 0
    scraped_count = 0

    try:
        driver = setup_driver(headless=False)

        query = keyword.replace(" ", "+")
        results_per_page = 10
        page = 0

        while scraped_count < max_results:
            start = page * results_per_page
            url = f"https://scholar.google.com/scholar?q={query}
            &start={start}"

            print(f"\n📄 Halaman {page+1}")
            driver.get(url)

            human_like_delay(3, 6)

            if not wait_for_captcha_if_needed(driver):
                print("❌ CAPTCHA gagal")
                break

            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".gs_r.gs_or"
                ".gs_scl"))
            )

            results = driver.find_elements(
                By.CSS_SELECTOR, ".gs_r.gs_or.gs_scl")

            if not results:
                print("❌ Tidak ada hasil lagi")
                break

            for result in results:
                if scraped_count >= max_results:
                    break

                row = {
                    "title": "",
                    "authors": "",
                    "year": None,
                    "source": "",
                    "abstract": "",
                    "citations": 0,
                    "url": "",
                    "pdf_url": None,
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

                    if not row["title"] or len(row["title"]) < 5:
                        print("⏭ skip: judul tidak valid")
                        continue

                    print("📄", row["title"][:70])

                except Exception as e:
                    print("⚠ error title:", e)
                    continue

                # =========================
                # DUPLICATE CHECK
                # =========================
                try:
                    existing = supabase.table(TABLE_NAME).select("id").eq("url", 
                    row["url"]).execute()
                    if existing.data:
                        print("⚠ sudah ada")
                        continue
                except:
                    pass

                # =========================
                # AUTHORS, YEAR, SOURCE
                # =========================
                try:
                    info = result.find_element(By.CSS_SELECTOR, ".gs_a").text
                    parts = info.split(" - ")

                    row["authors"] = parts[0].strip()
                    rest = parts[1] if len(parts) > 1 else ""

                    year_match = re.search(r"\b(19|20)\d{2}\b", rest)

                    if year_match:
                        row["year"] = int(year_match.group())
                        row["source"] = clean_source(rest, row["year"])
                    else:
                        row["source"] = ""

                except Exception as e:
                    print("⚠ parsing gs_a error:", e)
                    row["source"] = ""

                # =========================
                # FILTER TAHUN
                # =========================
                if row["year"] is None or not (2021 <= row["year"] <= 2026):
                    print("⏭ skip tahun:", row["year"])
                    continue

                # =========================
                # FILTER SOURCE (🔥 penting)
                # =========================
                if not row["source"]:
                    print("⏭ skip: source tidak valid")
                    continue

                # =========================
                # ABSTRACT
                # =========================
                try:
                    row["abstract"] = result.find_element(
                        By.CSS_SELECTOR, ".gs_rs").text
                except:
                    row["abstract"] = ""

                if not row["abstract"] or len(row["abstract"]) < 20:
                    print("⏭ skip: abstract jelek")
                    continue

                # =========================
                # VALID COUNT
                # =========================
                scraped_count += 1
                print(f"[{scraped_count}] ✅ artikel valid")
                print("\n" + "-"*50)
                print(f" Judul   : {row['title']}")
                print(f" Abstrak : {row['abstract'][:200]}")  # biar tidak kepanjangan
                print(f" Penulis : {row['authors']}")
                print(f" Tahun   : {row['year']}")
                print(f" Sumber  : {row['source']}")
                print("-"*50)

                # =========================
                # CITATIONS
                # =========================
                try:
                    cite = result.find_elements(By.CSS_SELECTOR, "a[href*='cites']")
                    if cite:
                        row["citations"] = int(
                            re.search(r"\d+", cite[0].text).group())
                except:
                    pass

                # =========================
                # PDF (FIXED)
                # =========================
                try:
                    pdf_el = result.find_element(By.CSS_SELECTOR, ".gs_or_ggsm a")
                    pdf_url = pdf_el.get_attribute("href")

                    row["pdf_url"] = pdf_url if pdf_url else None

                    if pdf_url:
                        #print("📥 PDF URL:", pdf_url[:60])

                        pdf_path = download_pdf(pdf_url, row["title"])

                        if pdf_path:
                            row["scrape_status"] = "pdf_downloaded"
                        else:
                            row["scrape_status"] = "pdf_failed"
                    else:
                        row["scrape_status"] = "no_pdf"

                except Exception as e:
                    print("⚠ tidak ada PDF:", e)
                    row["pdf_url"] = None
                    row["scrape_status"] = "no_pdf"

                # =========================
                # SAVE
                # =========================
                try:
                    supabase.table(TABLE_NAME).insert(row).execute()
                    success += 1
                except Exception as e:
                    print("⚠ gagal insert:", e)

                human_like_delay(2, 4)

            page += 1

    finally:
        if driver:
            driver.quit()

        print("\n" + "="*50)
        print(f"✅ SELESAI: {success}/{max_results}")
        print("="*50)