from app.search_engine import reload_search_index, search_articles
from app.services.ir_index_service import (
    rebuild_tfidf_index,
    sync_cleaned_dataset_from_final,
)
from src.scraper.pipeline import (
    METADATA_SIMILARITY_THRESHOLD,
    _new_skip_reasons,
    process_filtered_articles_for_doi_pdf,
    save_articles_incremental_to_supabase,
)
from src.scraper.scholar_scraper import scrape_and_collect_google_scholar
from src.scraper.similarity_service import filter_articles_by_similarity_and_source


def _emit(progress_callback, payload):
    if callable(progress_callback):
        progress_callback(payload)


def _category_for_dataset(keyword, selected_category=None):
    category = (selected_category or "").strip()
    if category:
        return category
    return keyword.strip().lower()


def _validation_progress_mapper(progress_callback):
    def handle(payload):
        payload = payload or {}
        event = payload.get("event")
        message = payload.get("message")

        if event == "article_start":
            _emit(progress_callback, {
                **payload,
                "stage": "doi",
                "message": message or "Melakukan DOI Resolution...",
            })
            return

        if event == "pdf_start":
            _emit(progress_callback, {
                **payload,
                "stage": "pdf",
                "message": message or "Melakukan PDF Validation...",
            })
            return

        _emit(progress_callback, payload)

    return handle


def run_web_ir_pipeline(
    keyword,
    target=10,
    selected_category=None,
    year_start=None,
    year_end=None,
    jenis_artikel=None,
    jenis_analisis=None,
    jumlah_publikasi=None,
    jumlah_kemunculan=None,
    progress_callback=None,
):
    """Menjalankan pipeline penelitian dari web dengan perubahan minimal."""
    keyword = (keyword or "").strip()
    if not keyword:
        raise ValueError("Keyword tidak boleh kosong")

    target = max(1, min(int(target or 10), 50))
    dataset_category = _category_for_dataset(keyword, selected_category)
    scrape_target = max(target, 10)

    _emit(progress_callback, {
        "stage": "start",
        "event": "start",
        "message": "Menyiapkan pipeline Information Retrieval...",
        "keyword": keyword,
        "category": dataset_category,
        "target": target,
    })
    _emit(progress_callback, {
        "stage": "start",
        "event": "done",
        "message": "Pipeline dimulai dari Google Scholar",
    })

    _emit(progress_callback, {
        "stage": "scrape",
        "event": "start",
        "message": "Mengambil metadata artikel dari Google Scholar...",
        "target": scrape_target,
    })
    (
        temporary_dataset,
        scraping_skip_reasons,
        scraping_skipped_total,
        scraped_count,
        _next_page,
        _has_more_pages,
    ) = scrape_and_collect_google_scholar(
        keyword,
        dataset_category,
        max_results=scrape_target,
        start_page=0,
        pages_to_collect=None,
        progress_callback=progress_callback,
    )
    _emit(progress_callback, {
        "stage": "scrape",
        "event": "done",
        "message": f"Scraping selesai: {scraped_count} artikel masuk Temporary Dataset",
        "temporary_count": len(temporary_dataset),
        "skipped_total": scraping_skipped_total,
        "skip_reasons": scraping_skip_reasons,
    })
    _emit(progress_callback, {
        "stage": "temporary",
        "event": "done",
        "message": f"Temporary Dataset siap: {len(temporary_dataset)} artikel",
        "temporary_count": len(temporary_dataset),
    })

    saved_summary = {"inserted": 0, "updated": 0, "saved_count": 0, "rows": []}
    filtered_candidates = []
    processed_articles = []
    final_skip_reasons = _new_skip_reasons()

    if temporary_dataset:
        _emit(progress_callback, {
            "stage": "preprocessing",
            "event": "start",
            "message": "Membersihkan metadata judul dan abstrak...",
            "temporary_count": len(temporary_dataset),
        })
        _emit(progress_callback, {
            "stage": "preprocessing",
            "event": "done",
            "message": "Preprocessing Temporary Dataset selesai",
            "temporary_count": len(temporary_dataset),
        })

        _emit(progress_callback, {
            "stage": "tfidf",
            "event": "start",
            "message": "Menghitung TF-IDF Temporary Dataset...",
        })
        _emit(progress_callback, {
            "stage": "vsm",
            "event": "start",
            "message": "Membentuk Vector Space Model Temporary Dataset...",
        })
        _emit(progress_callback, {
            "stage": "cosine",
            "event": "start",
            "message": "Menghitung Cosine Similarity antar metadata artikel...",
        })
        filtered_candidates = filter_articles_by_similarity_and_source(
            temporary_dataset,
            METADATA_SIMILARITY_THRESHOLD,
            progress_callback=None,
        )
        removed_duplicate = len(temporary_dataset) - len(filtered_candidates)
        final_skip_reasons.update(scraping_skip_reasons)
        final_skip_reasons["metadata_dup"] = removed_duplicate

        _emit(progress_callback, {
            "stage": "tfidf",
            "event": "done",
            "message": "TF-IDF Temporary Dataset selesai",
        })
        _emit(progress_callback, {
            "stage": "vsm",
            "event": "done",
            "message": "VSM Temporary Dataset selesai",
        })
        _emit(progress_callback, {
            "stage": "cosine",
            "event": "done",
            "message": "Cosine Similarity Temporary Dataset selesai",
            "candidate_count": len(filtered_candidates),
        })
        _emit(progress_callback, {
            "stage": "group",
            "event": "done",
            "message": f"Duplicate Grouping selesai: {removed_duplicate} duplikat metadata",
            "duplicate_count": removed_duplicate,
        })
        _emit(progress_callback, {
            "stage": "source",
            "event": "done",
            "message": f"Official Source Selection selesai: {len(filtered_candidates)} kandidat",
            "candidate_count": len(filtered_candidates),
        })

        _emit(progress_callback, {
            "stage": "doi",
            "event": "start",
            "message": "Melakukan DOI Resolution...",
            "candidate_count": len(filtered_candidates),
        })
        processed_articles, validation_skipped = process_filtered_articles_for_doi_pdf(
            filtered_candidates,
            final_skip_reasons,
            target_limit=target,
            progress_callback=_validation_progress_mapper(progress_callback),
            skip_existing=False,
        )
        _emit(progress_callback, {
            "stage": "doi",
            "event": "done",
            "message": "DOI Resolution selesai",
            "processed_count": len(processed_articles),
            "skipped_count": validation_skipped,
        })
        _emit(progress_callback, {
            "stage": "pdf",
            "event": "done",
            "message": "PDF Validation selesai",
            "processed_count": len(processed_articles),
        })
        _emit(progress_callback, {
            "stage": "final_dataset",
            "event": "done",
            "message": f"Final Dataset kandidat siap: {len(processed_articles)} artikel",
            "final_count": len(processed_articles),
        })

        _emit(progress_callback, {
            "stage": "supabase",
            "event": "start",
            "message": "Menyimpan incremental update ke Supabase...",
            "final_count": len(processed_articles),
        })
        saved_summary = save_articles_incremental_to_supabase(
            processed_articles,
            progress_callback=progress_callback,
        )
    else:
        _emit(progress_callback, {
            "stage": "preprocessing",
            "event": "done",
            "message": "Temporary Dataset kosong, tidak ada artikel baru untuk diproses",
        })
        _emit(progress_callback, {
            "stage": "supabase",
            "event": "done",
            "message": "Tidak ada artikel baru untuk disimpan",
        })

    saved_ids = [
        row.get("id")
        for row in saved_summary.get("rows", [])
        if row.get("id") is not None
    ]
    sync_cleaned_dataset_from_final(
        source_ids=saved_ids or None,
        progress_callback=progress_callback,
    )
    rebuild_tfidf_index(progress_callback=progress_callback)

    _emit(progress_callback, {
        "stage": "search",
        "event": "start",
        "message": "Memuat ulang indeks dan menyiapkan hasil pencarian...",
    })
    reload_info = reload_search_index()
    result = search_articles(
        query=keyword,
        top_k=target,
        year_start=year_start,
        year_end=year_end,
        jenis_artikel=jenis_artikel,
        jenis_analisis=jenis_analisis,
        jumlah_kemunculan=jumlah_kemunculan,
        jumlah_publikasi=jumlah_publikasi,
        kategori=selected_category or None,
        progress_callback=progress_callback,
    )
    result["pipeline_summary"] = {
        "search_mode": "scraping_incremental",
        "scraping_executed": True,
        "temporary_count": len(temporary_dataset),
        "candidate_count": len(filtered_candidates),
        "processed_count": len(processed_articles),
        "inserted": saved_summary.get("inserted", 0),
        "updated": saved_summary.get("updated", 0),
        "index": reload_info,
    }
    _emit(progress_callback, {
        "stage": "search",
        "event": "done",
        "message": "Hasil pencarian siap ditampilkan",
        "displayed_count": result.get("displayed_count", 0),
    })
    return result
