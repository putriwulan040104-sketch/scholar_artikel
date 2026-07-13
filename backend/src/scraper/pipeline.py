from datetime import datetime, timezone

from src.config.supabase_client import supabase
from src.scraper.doi_service import (
    fetch_doi_crossref,
    fetch_doi_from_doi_org,
    select_pdf_url_for_article,
)
from src.scraper.pdf_handler import download_pdf, extract_doi_from_pdf
from src.scraper.scholar_scraper import scrape_and_collect_google_scholar
from src.scraper.similarity_service import filter_articles_by_similarity_and_source
from src.scraper.source_selector import classify_pdf_source, log_pdf_source_validation


TABLE_DOI = "scholar_articles_doi"
METADATA_SIMILARITY_THRESHOLD = 0.95
METADATA_BUFFER_MULTIPLIER = 2
MIN_METADATA_BATCH_SIZE = 50
TEMPORARY_SCRAPING_DATASET = []
FILTERED_SCRAPING_DATASET = []
CURRENT_PROCESS_STATUS = None
PROCESSING_CACHE = {}


def _emit_progress(progress_callback, payload):
    if callable(progress_callback):
        progress_callback(payload)


def log_process_status(status, article_count=None):
    """Menampilkan status pipeline agar backend dapat dilacak per tahap proses."""
    global CURRENT_PROCESS_STATUS

    CURRENT_PROCESS_STATUS = status
    print(f"\n{'='*65}")
    print(f"PROCESS STATUS : {status}")
    if article_count is not None:
        print(f"Article Count  : {article_count}")
    print(f"{'='*65}")


def get_scraping_process_status():
    """Mengembalikan status pipeline terakhir untuk kebutuhan monitoring dari backend."""
    return CURRENT_PROCESS_STATUS


def get_temporary_scraping_results():
    """Mengembalikan dataset sementara agar Flask dapat menampilkannya sebelum insert DB."""
    display_fields = [
        "title", "abstract", "authors", "year", "source", "url",
        "pdf_url", "category",
    ]
    return [
        {field: article.get(field) for field in display_fields}
        for article in TEMPORARY_SCRAPING_DATASET
    ]


def get_filtered_scraping_results():
    """Mengembalikan artikel final setelah similarity checking dan official source selection."""
    return [article.copy() for article in FILTERED_SCRAPING_DATASET]


def _exists(field, value):
    """Mengecek keberadaan value tertentu di tabel Supabase tujuan."""
    if not value:
        return False
    try:
        res = supabase.table(TABLE_DOI).select("id").eq(field, value).limit(1).execute()
        return bool(res.data)
    except Exception:
        return False


is_doi_dup = lambda v: _exists("doi", v)
is_url_dup = lambda v: _exists("url", v)
is_pdfurl_dup = lambda v: _exists("pdf_url", v)


def _new_skip_reasons():
    """Membuat counter skip standar agar ringkasan tiap iterasi konsisten."""
    return {
        "judul": 0, "url_dup": 0, "tahun": 0, "source": 0,
        "abstract": 0, "doi": 0, "doi_dup": 0,
        "pdfurl_dup": 0, "pdf_failed": 0, "metadata_dup": 0,
        "disimpan": 0,
    }


def _merge_skip_reasons(total, batch):
    """Menggabungkan counter skip dari scraping batch ke total pipeline."""
    for key, value in batch.items():
        total[key] = total.get(key, 0) + value


def _article_cache_key(row):
    """Membuat key cache stabil untuk satu artikel selama satu proses scraping."""
    if row.get("url"):
        return f"url:{row.get('url')}"
    return "meta:{title}|{year}|{source}".format(
        title=(row.get("title") or "").strip().lower(),
        year=row.get("year") or "",
        source=(row.get("source") or "").strip().lower(),
    )


def _store_processing_skip(processing_cache, cache_key, reason):
    """Menyimpan hasil skip yang mahal agar DOI/PDF tidak diproses ulang."""
    if processing_cache is not None and cache_key:
        processing_cache[cache_key] = {
            "status": "skip",
            "reason": reason,
        }


def _store_processing_success(processing_cache, cache_key, row):
    """Menyimpan hasil DOI dan PDF valid agar artikel lama tidak diunduh ulang."""
    if processing_cache is not None and cache_key:
        cached_row = row.copy()
        cached_row.pop("scraped_at", None)
        processing_cache[cache_key] = {
            "status": "success",
            "row": cached_row,
        }


def process_filtered_articles_for_doi_pdf(
    articles,
    skip_reasons,
    target_limit=None,
    progress_callback=None,
):
    """Menjalankan tahap DOI, official PDF, download PDF, validasi PDF, dan duplicate DB pada artikel final."""
    global PROCESSING_CACHE

    processed_articles = []
    skipped_count = 0
    accepted_urls = set()
    accepted_dois = set()
    accepted_pdf_urls = set()
    processing_cache = PROCESSING_CACHE

    total_articles = len(articles)
    for index, source_row in enumerate(articles, start=1):
        if target_limit is not None and len(processed_articles) >= target_limit:
            break

        row = source_row.copy()
        article_url = row.get("url")
        cache_key = _article_cache_key(row)
        title_preview = (row.get("title") or "Artikel").strip()
        if len(title_preview) > 90:
            title_preview = f"{title_preview[:87]}..."

        _emit_progress(progress_callback, {
            "stage": "validate",
            "event": "article_start",
            "message": f"Sedang memeriksa DOI: {title_preview}",
            "current": index,
            "total": total_articles,
            "accepted_count": len(processed_articles),
            "skipped_count": skipped_count,
        })

        if article_url and article_url in accepted_urls:
            print("Skip: URL sudah lolos pada final dataset sementara")
            skip_reasons["url_dup"] += 1
            skipped_count += 1
            continue

        if is_url_dup(article_url):
            print("Skip: URL sudah ada di DB")
            skip_reasons["url_dup"] += 1
            skipped_count += 1
            continue

        cached_processing = None
        if processing_cache is not None:
            cached_processing = processing_cache.get(cache_key)

        if cached_processing and cached_processing.get("status") == "skip":
            reason = cached_processing.get("reason")
            if reason in skip_reasons:
                skip_reasons[reason] += 1
            skipped_count += 1
            if reason == "doi":
                print("Skip: DOI tidak ditemukan pada final dataset")
            elif reason == "pdf_failed":
                print("Skip: PDF gagal / tidak tersedia")
            else:
                print("Skip: artikel sudah pernah gagal diproses")
            continue

        if cached_processing and cached_processing.get("status") == "success":
            row = cached_processing["row"].copy()
            doi_article = row.get("doi")
            pdf_url = row.get("pdf_url")
            pdf_doi = row.get("pdf_doi")
            access = row.get("access_type")
            status = row.get("scrape_status")
        else:
            doi_article = None

            log_process_status("DOI Resolution", len(articles))
            doi_article = fetch_doi_from_doi_org(row.get("url"))

            if not doi_article:
                doi_article = fetch_doi_crossref(row["title"], row.get("authors", ""))

            if not doi_article:
                print("Skip: DOI tidak ditemukan pada final dataset")
                skip_reasons["doi"] += 1
                skipped_count += 1
                _emit_progress(progress_callback, {
                    "stage": "validate",
                    "event": "article_skip",
                    "message": "DOI tidak ditemukan, artikel dilewati",
                    "current": index,
                    "total": total_articles,
                    "accepted_count": len(processed_articles),
                    "skipped_count": skipped_count,
                })
                _store_processing_skip(processing_cache, cache_key, "doi")
                continue

            if doi_article in accepted_dois:
                print(f"Skip: DOI {doi_article} sudah lolos pada final dataset sementara")
                skip_reasons["doi_dup"] += 1
                skipped_count += 1
                continue

            scholar_pdf_url = row.get("pdf_url")
            row["pdf_url"] = select_pdf_url_for_article(doi_article, scholar_pdf_url)
            row.update(classify_pdf_source(row.get("pdf_url")))

            pdf_url = row.get("pdf_url")
            pdf_doi = None
            access = "closed_access"
            status = "metadata_only"

            if pdf_url and pdf_url in accepted_pdf_urls:
                print("Skip: PDF URL sudah lolos pada final dataset sementara")
                skip_reasons["pdfurl_dup"] += 1
                skipped_count += 1
                continue

            log_process_status("PDF Download", len(articles))
            if pdf_url:
                _emit_progress(progress_callback, {
                    "stage": "validate",
                    "event": "pdf_start",
                    "message": "Sedang memeriksa ketersediaan PDF...",
                    "current": index,
                    "total": total_articles,
                })
                pdf_info = {
                    "pdf_domain": row.get("pdf_domain"),
                    "pdf_source_type": row.get("pdf_source_type"),
                    "is_official_pdf": row.get("is_official_pdf", False),
                }
                log_pdf_source_validation(row["source"], pdf_info)

                pdf_path = download_pdf(pdf_url, row["title"])

                log_process_status("PDF Validation", len(articles))
                if pdf_path:
                    access = "open_access"
                    status = "pdf_downloaded"
                    pdf_doi = extract_doi_from_pdf(pdf_path)

                    if pdf_doi:
                        if pdf_doi == doi_article:
                            print(f"  [LEVEL A] DOI cocok: {doi_article}")
                        else:
                            print(
                                f"  [LEVEL A*] DOI berbeda (preprint?):\n"
                                f"     artikel  : {doi_article}\n"
                                f"     pdf      : {pdf_doi}"
                            )
                    else:
                        print(f"  [LEVEL B] PDF ada, pdf_doi tidak embed")

                else:
                    # ===== LEVEL C =====
                    access = "closed_access"
                    status = "metadata_only"
                    pdf_doi = None

                    print("  [LEVEL C] PDF tidak tersedia")
            else:
                log_process_status("PDF Validation", len(articles))

                access = "closed_access"
                status = "metadata_only"
                pdf_doi = None

                print("  [LEVEL C] Tidak ada URL PDF")

            row["doi"] = doi_article
            row["pdf_url"] = pdf_url
            row["pdf_doi"] = pdf_doi
            row["access_type"] = access
            row["scrape_status"] = status
            _store_processing_success(processing_cache, cache_key, row)

        if doi_article in accepted_dois:
            print(f"Skip: DOI {doi_article} sudah lolos pada final dataset sementara")
            skip_reasons["doi_dup"] += 1
            skipped_count += 1
            continue

        if pdf_url and pdf_url in accepted_pdf_urls:
            print("Skip: PDF URL sudah lolos pada final dataset sementara")
            skip_reasons["pdfurl_dup"] += 1
            skipped_count += 1
            continue

        if is_doi_dup(doi_article):
            print(f"Skip: DOI {doi_article} sudah ada di DB")
            skip_reasons["doi_dup"] += 1
            skipped_count += 1
            continue

        if pdf_url and is_pdfurl_dup(pdf_url):
            print("Skip: PDF URL sudah ada di DB")
            skip_reasons["pdfurl_dup"] += 1
            skipped_count += 1
            continue

        row["doi"] = doi_article
        row["pdf_url"] = pdf_url
        row["pdf_doi"] = pdf_doi
        row["access_type"] = access
        row["scrape_status"] = status
        row["scraped_at"] = datetime.now(timezone.utc).isoformat()
        processed_articles.append(row)
        if article_url:
            accepted_urls.add(article_url)
        accepted_dois.add(doi_article)
        if pdf_url:
            accepted_pdf_urls.add(pdf_url)

        _emit_progress(progress_callback, {
            "stage": "validate",
            "event": "article_done",
            "message": f"Artikel valid: {len(processed_articles)}",
            "current": index,
            "total": total_articles,
            "accepted_count": len(processed_articles),
            "skipped_count": skipped_count,
            "doi": doi_article,
            "pdf_status": status,
        })

    return processed_articles, skipped_count


def save_articles_to_supabase(articles, progress_callback=None):
    """Menyimpan artikel final ke Supabase setelah seluruh filtering selesai."""
    success = 0
    total = len(articles)
    for index, row in enumerate(articles, start=1):
        _emit_progress(progress_callback, {
            "stage": "save",
            "event": "article_start",
            "message": f"Sedang menyimpan hasil {index}/{total}...",
            "current": index,
            "total": total,
            "saved_count": success,
        })
        try:
            db_row = row.copy()
            db_row.pop("publisher", None)
            supabase.table(TABLE_DOI).insert(db_row).execute()
            success += 1
        except Exception as e:
            print(f"  Gagal insert Supabase: {e}")
    _emit_progress(progress_callback, {
        "stage": "save",
        "event": "done",
        "message": f"Hasil tersimpan: {success} artikel",
        "saved_count": success,
        "total": total,
    })
    return success


def scrape_and_save_to_supabase_legacy(keyword, category, max_results=50):
    """Arsip alur lama: target masih dihitung dari temporary dataset, bukan artikel final."""
    global TEMPORARY_SCRAPING_DATASET, FILTERED_SCRAPING_DATASET

    success = 0
    log_process_status("Scraping Metadata", 0)
    (
        TEMPORARY_SCRAPING_DATASET,
        skip_reasons,
        skipped_total,
        scraped_count,
    ) = scrape_and_collect_google_scholar(keyword, category, max_results)

    log_process_status("Temporary Dataset Ready", len(TEMPORARY_SCRAPING_DATASET))
    print(f"   Total temporary artikel : {len(TEMPORARY_SCRAPING_DATASET)}")
    print(f"Temporary Dataset : {len(TEMPORARY_SCRAPING_DATASET)} artikel")
    print("   Mulai similarity checking dan official source selection...")

    log_process_status("Similarity Checking", len(TEMPORARY_SCRAPING_DATASET))
    log_process_status("Duplicate Grouping", len(TEMPORARY_SCRAPING_DATASET))
    log_process_status("Official Source Selection", len(TEMPORARY_SCRAPING_DATASET))
    FILTERED_SCRAPING_DATASET = filter_articles_by_similarity_and_source(
        TEMPORARY_SCRAPING_DATASET,
        METADATA_SIMILARITY_THRESHOLD,
    )
    removed_by_similarity = (
        len(TEMPORARY_SCRAPING_DATASET) - len(FILTERED_SCRAPING_DATASET)
    )
    skip_reasons["metadata_dup"] += removed_by_similarity
    skipped_total += removed_by_similarity
    print(f"Similarity Filtering : {len(FILTERED_SCRAPING_DATASET)} artikel")
    print(f"Official Source Selection : {len(FILTERED_SCRAPING_DATASET)} artikel")

    log_process_status("Final Dataset Ready", len(FILTERED_SCRAPING_DATASET))
    print(f"   Temporary artikel : {len(TEMPORARY_SCRAPING_DATASET)}")
    print(f"   Final artikel     : {len(FILTERED_SCRAPING_DATASET)}")
    print(f"   Removed duplicate : {removed_by_similarity}")

    FILTERED_SCRAPING_DATASET, final_processing_skips = (
        process_filtered_articles_for_doi_pdf(FILTERED_SCRAPING_DATASET, skip_reasons)
    )
    skipped_total += final_processing_skips

    log_process_status("Insert Supabase", len(FILTERED_SCRAPING_DATASET))
    success = save_articles_to_supabase(FILTERED_SCRAPING_DATASET)
    print(f"Insert Supabase : {success} artikel")
    skip_reasons["disimpan"] = success

    print(f"\n{'='*65}")
    print("✅ SELESAI SCRAPING")
    print(f"   Berhasil disimpan  : {success} artikel")
    print(f"   Temporary dataset  : {len(TEMPORARY_SCRAPING_DATASET)} artikel")
    print(f"   Final dataset      : {len(FILTERED_SCRAPING_DATASET)} artikel")
    print(f"   Target             : {max_results} artikel")
    print(f"   Total di-skip      : {skipped_total}")
    print()
    print("  RINCIAN SKIP / UPDATE:")
    labels = {
        "judul":      "Judul tidak valid",
        "url_dup":    "URL duplikat",
        "tahun":      "Tahun di luar range",
        "source":     "Source tidak valid",
        "abstract":   "Abstract tidak valid",
        "doi":        "DOI tidak ditemukan",
        "doi_dup":    "DOI duplikat",
        "pdfurl_dup": "PDF URL duplikat",
        "pdf_failed": "PDF gagal / tidak tersedia",
        "metadata_dup": "Metadata duplikat",
    }
    for k, label in labels.items():
        if skip_reasons[k]:
            print(f"    {label:<28}: {skip_reasons[k]}")
    print(f"{'='*65}")

    return FILTERED_SCRAPING_DATASET


def scrape_and_save_to_supabase(keyword, category, max_results=50, progress_callback=None):
    """Menjalankan pipeline sampai target dihitung dari artikel final valid."""
    global TEMPORARY_SCRAPING_DATASET, FILTERED_SCRAPING_DATASET, PROCESSING_CACHE

    target_final_articles = max_results
    next_page = 0
    has_more_pages = True
    success = 0
    scraping_skipped_total = 0
    latest_skipped_total = 0
    scraping_skip_reasons = _new_skip_reasons()
    latest_skip_reasons = _new_skip_reasons()

    TEMPORARY_SCRAPING_DATASET = []
    FILTERED_SCRAPING_DATASET = []
    PROCESSING_CACHE = {}

    print(f"\n{'='*65}")
    print(f"TARGET FINAL VALID ARTICLE : {target_final_articles}")
    print(f"{'='*65}")
    _emit_progress(progress_callback, {
        "stage": "start",
        "event": "done",
        "message": (
            f"Pencarian dimulai untuk keyword '{keyword}' "
            f"dengan target {target_final_articles} artikel"
        ),
        "target": target_final_articles,
        "keyword": keyword,
        "category": category,
    })

    while len(FILTERED_SCRAPING_DATASET) < target_final_articles and has_more_pages:
        log_process_status("Scraping Metadata", len(TEMPORARY_SCRAPING_DATASET))
        
        need_more = max( target_final_articles - len(FILTERED_SCRAPING_DATASET),
            0
        )

        # Ambil secukupnya saja
        if need_more <= 5:
            temp_target = 10

        elif need_more <= 10:
            temp_target = need_more * 2

        else:
            temp_target = min(
                need_more * 2,
                30
            )

        print(f"Need More Final Article : {need_more}")
        print(f"Scraping Batch Target   : {temp_target}")
        _emit_progress(progress_callback, {
            "stage": "scrape",
            "event": "start",
            "message": "Mengambil artikel dari Google Scholar...",
            "temporary_count": len(TEMPORARY_SCRAPING_DATASET),
            "valid_count": len(FILTERED_SCRAPING_DATASET),
            "need_more": need_more,
            "batch_target": temp_target,
        })
        (
            batch_dataset,
            batch_skip_reasons,
            batch_skipped_total,
            _batch_scraped_count,
            next_page,
            has_more_pages,
        ) = scrape_and_collect_google_scholar(
            keyword,
            category,
            max_results=temp_target,
            start_page=next_page,
            pages_to_collect=None,
            progress_callback=progress_callback,
        )

        TEMPORARY_SCRAPING_DATASET.extend(batch_dataset)
        _merge_skip_reasons(scraping_skip_reasons, batch_skip_reasons)
        scraping_skipped_total += batch_skipped_total
        _emit_progress(progress_callback, {
            "stage": "scrape",
            "event": "done",
            "message": f"Total artikel sementara: {len(TEMPORARY_SCRAPING_DATASET)}",
            "temporary_count": len(TEMPORARY_SCRAPING_DATASET),
            "skipped_total": scraping_skipped_total,
        })

        if not TEMPORARY_SCRAPING_DATASET:
            if not has_more_pages:
                break
            continue

        log_process_status("Temporary Dataset Ready", len(TEMPORARY_SCRAPING_DATASET))
        _emit_progress(progress_callback, {
            "stage": "filter",
            "event": "start",
            "message": "Menyaring artikel yang memenuhi kriteria awal...",
            "temporary_count": len(TEMPORARY_SCRAPING_DATASET),
            "skipped_total": scraping_skipped_total,
        })
        print(f"   Total temporary artikel : {len(TEMPORARY_SCRAPING_DATASET)}")
        print(f"Temporary Dataset : {len(TEMPORARY_SCRAPING_DATASET)} artikel")
        print("   Mulai similarity checking dan official source selection...")
        _emit_progress(progress_callback, {
            "stage": "filter",
            "event": "done",
            "message": (
                f"Artikel valid: {len(TEMPORARY_SCRAPING_DATASET)} | "
                f"Artikel dilewati: {scraping_skipped_total}"
            ),
            "temporary_count": len(TEMPORARY_SCRAPING_DATASET),
            "skipped_total": scraping_skipped_total,
            "skip_reasons": scraping_skip_reasons.copy(),
        })

        log_process_status("Similarity Checking", len(TEMPORARY_SCRAPING_DATASET))
        log_process_status("Duplicate Grouping", len(TEMPORARY_SCRAPING_DATASET))
        log_process_status("Official Source Selection", len(TEMPORARY_SCRAPING_DATASET))
        filtered_candidates = filter_articles_by_similarity_and_source(
            TEMPORARY_SCRAPING_DATASET,
            METADATA_SIMILARITY_THRESHOLD,
            progress_callback=progress_callback,
        )
        removed_by_similarity = len(TEMPORARY_SCRAPING_DATASET) - len(filtered_candidates)

        latest_skip_reasons = scraping_skip_reasons.copy()
        latest_skip_reasons["metadata_dup"] = removed_by_similarity

        print(f"Similarity Filtering : {len(filtered_candidates)} artikel")
        print(f"Official Source Selection : {len(filtered_candidates)} artikel")

        log_process_status("Final Dataset Ready", len(filtered_candidates))
        print(f"   Temporary artikel : {len(TEMPORARY_SCRAPING_DATASET)}")
        print(f"   Kandidat final    : {len(filtered_candidates)}")
        print(f"   Removed duplicate : {removed_by_similarity}")
        _emit_progress(progress_callback, {
            "stage": "group",
            "event": "summary",
            "message": f"Artikel duplikat: {removed_by_similarity}",
            "duplicate_count": removed_by_similarity,
            "candidate_count": len(filtered_candidates),
        })

        FILTERED_SCRAPING_DATASET, final_processing_skips = (
            process_filtered_articles_for_doi_pdf(
                filtered_candidates,
                latest_skip_reasons,
                target_limit=target_final_articles,
                progress_callback=progress_callback,
            )
        )
        _emit_progress(progress_callback, {
            "stage": "validate",
            "event": "done",
            "message": (
                f"Pemeriksaan DOI dan PDF selesai. "
                f"Artikel valid: {len(FILTERED_SCRAPING_DATASET)}"
            ),
            "valid_count": len(FILTERED_SCRAPING_DATASET),
            "skipped_count": final_processing_skips,
        })

        current_skipped_total = (
            scraping_skipped_total
            + removed_by_similarity
            + final_processing_skips
        )
        need_more_after_processing = max(target_final_articles - len(FILTERED_SCRAPING_DATASET), 0)

        print(f"\n{'='*65}")
        print(f"TARGET FINAL VALID ARTICLE : {target_final_articles}")
        print(f"{'='*65}")
        print(f"Temporary Articles Collected : {len(TEMPORARY_SCRAPING_DATASET)}")
        print(f"Valid Articles               : {len(FILTERED_SCRAPING_DATASET)}")
        print(f"Need More                    : {need_more_after_processing}")
        if need_more_after_processing and has_more_pages:
            print("Continue Scraping Next Page...")
        elif need_more_after_processing and not has_more_pages:
            print(
                f"Target {target_final_articles} artikel tidak tercapai. "
                f"Hanya ditemukan {len(FILTERED_SCRAPING_DATASET)} artikel final valid."
            )
        print(f"{'='*65}")

        latest_skipped_total = current_skipped_total

    log_process_status("Insert Supabase", len(FILTERED_SCRAPING_DATASET))
    _emit_progress(progress_callback, {
        "stage": "save",
        "event": "start",
        "message": "Sedang menyimpan hasil akhir...",
        "final_count": len(FILTERED_SCRAPING_DATASET),
    })
    success = save_articles_to_supabase(
        FILTERED_SCRAPING_DATASET,
        progress_callback=progress_callback,
    )
    print(f"Insert Supabase : {success} artikel")
    latest_skip_reasons["disimpan"] = success

    print(f"\n{'='*65}")
    print("SCRAPING FINISHED")
    print(f"Temporary Articles Collected : {len(TEMPORARY_SCRAPING_DATASET)}")
    print(f"Final Valid Articles         : {len(FILTERED_SCRAPING_DATASET)}")
    print(f"Inserted Into Supabase       : {success}")
    print(f"Target                       : {target_final_articles} artikel")
    print(f"Total di-skip                : {latest_skipped_total}")
    print()
    print("  RINCIAN SKIP / UPDATE:")
    labels = {
        "judul":      "Judul tidak valid",
        "url_dup":    "URL duplikat",
        "tahun":      "Tahun di luar range",
        "source":     "Source tidak valid",
        "abstract":   "Abstract tidak valid",
        "doi":        "DOI tidak ditemukan",
        "doi_dup":    "DOI duplikat",
        "pdfurl_dup": "PDF URL duplikat",
        "pdf_failed": "PDF gagal / tidak tersedia",
        "metadata_dup": "Metadata duplikat",
    }
    for key, label in labels.items():
        if latest_skip_reasons[key]:
            print(f"    {label:<28}: {latest_skip_reasons[key]}")
    print(f"{'='*65}")

    return FILTERED_SCRAPING_DATASET


# =============================================================================
# STEP-BY-STEP PIPELINE FUNCTIONS (UNTUK WEB UI)
# Berdasarkan arahan dosen: Sistem tidak boleh langsung insert ke DB.
# Seluruh tahapan harus bisa ditampilkan secara bertahap di web.
# =============================================================================

def pipeline_step_1_scraping(keyword, category, max_results=50, start_page=0, pages_to_collect=1):
    """
    Tahap 1: Scraping -> Temporary Dataset
    Hanya melakukan scraping data awal (Google Scholar) dan mengembalikan hasilnya
    sebagai temporary dataset untuk direview pengguna di UI.
    """
    log_process_status("Step 1: Scraping Metadata", 0)
    dataset, skip_reasons, skipped_total, scraped_count, next_page, has_more = scrape_and_collect_google_scholar(
        keyword, category, max_results=max_results, start_page=start_page, pages_to_collect=pages_to_collect
    )
    
    log_process_status("Step 1: Temporary Dataset Ready", len(dataset))
    return {
        "temporary_dataset": dataset,
        "skip_reasons": skip_reasons,
        "skipped_total": skipped_total,
        "scraped_count": scraped_count,
        "next_page": next_page,
        "has_more_pages": has_more
    }


def pipeline_step_2_similarity_and_filtering(temporary_dataset, threshold=METADATA_SIMILARITY_THRESHOLD):
    """
    Tahap 2: Similarity Checking (TF-IDF & VSM & Cosine Similarity) -> Duplicate Grouping -> Official Source Selection
    Menerima temporary dataset dari tahap 1, mencari artikel duplikat, dan memilih sumber resmi terbaik.
    """
    from src.scraper.similarity_service import group_duplicate_articles, select_best_article_from_group, get_group_similarity
    
    log_process_status("Step 2: Similarity Checking & Duplicate Grouping", len(temporary_dataset))
    
    if not temporary_dataset:
        return {"group_details": [], "similarity_matrix": [], "filtered_dataset": []}

    groups, similarity_matrix = group_duplicate_articles(temporary_dataset, threshold)
    
    selected_indexes = []
    group_details = []

    log_process_status("Step 2: Official Source Selection", len(groups))
    
    for idx, group_indexes in enumerate(groups):
        if len(group_indexes) == 1:
            selected_indexes.append(group_indexes[0])
            group_details.append({
                "group_number": idx + 1,
                "articles": [temporary_dataset[group_indexes[0]]],
                "selected_article": temporary_dataset[group_indexes[0]],
                "similarity_score": 1.0,
                "is_duplicate": False
            })
            continue

        keep_index = select_best_article_from_group(temporary_dataset, group_indexes)
        selected_indexes.append(keep_index)
        
        score = get_group_similarity(group_indexes, similarity_matrix)
        group_details.append({
            "group_number": idx + 1,
            "articles": [temporary_dataset[i] for i in group_indexes],
            "selected_article": temporary_dataset[keep_index],
            "similarity_score": float(score),
            "is_duplicate": True
        })

    selected_indexes.sort()
    filtered_dataset = [temporary_dataset[index] for index in selected_indexes]
    
    # Konversi matrix similarity numpy ke list of list agar bisa di-encode ke JSON untuk frontend
    sim_matrix_list = similarity_matrix.tolist() if hasattr(similarity_matrix, 'tolist') else similarity_matrix

    log_process_status("Step 2: Final Dataset Ready", len(filtered_dataset))
    return {
        "group_details": group_details,
        "similarity_matrix": sim_matrix_list,
        "filtered_dataset": filtered_dataset
    }


def pipeline_step_3_process_and_save(filtered_dataset):
    """
    Tahap 3: DOI Resolution -> PDF Validation -> Insert Database
    Menerima final dataset dari tahap 2, mencari DOI, validasi PDF, dan menyimpan ke Supabase.
    """
    log_process_status("Step 3: DOI Resolution & PDF Validation", len(filtered_dataset))
    skip_reasons = _new_skip_reasons()
    
    processed_articles, skipped_count = process_filtered_articles_for_doi_pdf(
        filtered_dataset, skip_reasons, target_limit=None
    )
    
    log_process_status("Step 3: Insert Database", len(processed_articles))
    success_count = save_articles_to_supabase(processed_articles)
    skip_reasons["disimpan"] = success_count
    
    log_process_status("Step 3: Pipeline Finished", success_count)
    return {
        "processed_articles": processed_articles,
        "saved_count": success_count,
        "skipped_count": skipped_count,
        "skip_reasons": skip_reasons
    }
