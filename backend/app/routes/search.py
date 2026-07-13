import copy
import json
import math
import queue
import threading
import time

from flask import Blueprint, Response, jsonify, request, stream_with_context
from app.search_engine import (
    get_article_by_id,
    get_category_options,
    get_relation_type_options,
    get_stats,
    search_articles,
    get_cosine_catalog,
)

search_bp = Blueprint("search", __name__)

SEARCH_PROGRESS_STAGES = [
    {
        "key": "start",
        "title": "Memulai Pencarian",
        "description": "Mencari artikel berdasarkan kata kunci dan kategori yang Anda pilih.",
    },
    {
        "key": "prepare",
        "title": "Menyiapkan Dataset Artikel",
        "description": "Menggunakan dataset artikel yang sudah tersedia di Supabase.",
    },
    {
        "key": "preprocessing",
        "title": "Melakukan Preprocessing",
        "description": "Membersihkan kata kunci dan menyiapkan term yang akan dicocokkan.",
    },
    {
        "key": "tfidf",
        "title": "Menghitung TF-IDF",
        "description": "Menghitung bobot kata kunci berdasarkan vocabulary dataset.",
    },
    {
        "key": "vsm",
        "title": "Menyiapkan Vector Space Model",
        "description": "Menempatkan query dan artikel pada ruang vektor yang sama.",
    },
    {
        "key": "cosine",
        "title": "Menghitung Cosine Similarity",
        "description": "Menghitung tingkat kecocokan query dengan setiap artikel.",
    },
    {
        "key": "filter",
        "title": "Menyaring Artikel Sesuai Kriteria",
        "description": "Menerapkan filter tahun, kategori, akses artikel, dan jenis analisis.",
    },
    {
        "key": "final",
        "title": "Menyusun Hasil Akhir",
        "description": "Mengurutkan artikel berdasarkan skor kecocokan dan menyiapkan data untuk ditampilkan.",
    },
]


def _initial_progress_stages():
    return [
        {
            **stage,
            "status": "waiting",
            "duration_seconds": 0,
            "details": {},
        }
        for stage in SEARCH_PROGRESS_STAGES
    ]


def _normalize_pipeline_articles(articles):
    normalized = []
    for index, article in enumerate(articles or [], start=1):
        pdf_url = article.get("pdf_url")
        url = article.get("url")
        normalized.append({
            "id": int(article.get("id") or index),
            "rank": index,
            "title": article.get("title") or "",
            "authors": article.get("authors") or "",
            "year": article.get("year"),
            "source": article.get("source") or "",
            "category": article.get("category") or "",
            "abstract": article.get("abstract") or "",
            "similarity_score": float(article.get("similarity_score") or 0),
            "pdf_url": pdf_url,
            "url": url,
            "access_url": pdf_url or url,
            "is_pdf": bool(pdf_url),
            "scrape_status": article.get("scrape_status") or "",
            "doi": article.get("doi"),
        })
    return normalized


def _json_safe(value):
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    if isinstance(value, float) and math.isnan(value):
        return None
    if hasattr(value, "item"):
        try:
            return _json_safe(value.item())
        except Exception:
            return str(value)
    return value


class SearchProgressReporter:
    def __init__(self, emit, keyword, category, target):
        self.emit = emit
        self.keyword = keyword
        self.category = category
        self.target = target
        self.started_at = time.time()
        self.monotonic_started_at = time.monotonic()
        self.stages = _initial_progress_stages()
        self.logs = []
        self.stage_started_at = {}
        self.finished = False
        self.error = None
        self.result = None

    def _stage_by_key(self, key):
        for stage in self.stages:
            if stage["key"] == key:
                return stage
        return None

    def _set_stage(self, key, status, details=None):
        stage = self._stage_by_key(key)
        if not stage:
            return
        if status == "running" and stage["status"] != "running":
            self.stage_started_at[key] = time.monotonic()
        if status == "done":
            started = self.stage_started_at.get(key)
            if started:
                stage["duration_seconds"] = int(time.monotonic() - started)
        stage["status"] = status
        if details:
            stage["details"].update(details)

    def _append_log(self, message):
        if not message:
            return
        self.logs.append({
            "message": message,
            "elapsed_seconds": int(time.monotonic() - self.monotonic_started_at),
        })
        self.logs = self.logs[-80:]

    def _progress_percent(self):
        done = sum(1 for stage in self.stages if stage["status"] == "done")
        running = 1 if any(stage["status"] == "running" for stage in self.stages) else 0
        return min(100, int(((done + (0.45 * running)) / len(self.stages)) * 100))

    def snapshot(self, event="progress", message=None):
        return {
            "event": event,
            "keyword": self.keyword,
            "category": self.category,
            "target": self.target,
            "status": "error" if self.error else ("complete" if self.finished else "running"),
            "message": message or (self.logs[-1]["message"] if self.logs else ""),
            "progress": 100 if self.finished and not self.error else self._progress_percent(),
            "elapsed_seconds": int(time.monotonic() - self.monotonic_started_at),
            "stages": copy.deepcopy(self.stages),
            "logs": copy.deepcopy(self.logs),
            "result": copy.deepcopy(self.result),
            "error": self.error,
        }

    def handle(self, payload):
        payload = payload or {}
        key = payload.get("stage")
        event = payload.get("event")
        message = payload.get("message")
        details = {
            k: v for k, v in payload.items()
            if k not in {"stage", "event", "message"}
        }
        if message:
            details["message"] = message

        if event in {"start", "page_start", "article_start", "pdf_start"}:
            self._set_stage(key, "running", details)
        elif event == "done":
            self._set_stage(key, "done", details)
        elif key:
            stage = self._stage_by_key(key)
            if stage:
                self._set_stage(key, stage["status"], details)

        self._append_log(message)
        self.emit(self.snapshot(message=message))

    def complete(self, result):
        for stage in self.stages:
            if stage["status"] == "running":
                self._set_stage(stage["key"], "done")
        if isinstance(result, dict):
            articles = _json_safe(result.get("articles") or [])
            total = int(result.get("total_matched", len(articles)) or 0)
            total_occurrences = int(result.get("total_occurrences", 0) or 0)
            paper_count = int(result.get("paper_count", len(articles)) or 0)
        else:
            articles = _normalize_pipeline_articles(result)
            total = len(articles)
            total_occurrences = 0
            paper_count = len(articles)

        self.result = {
            "articles": articles,
            "total": total,
            "total_matched": total,
            "total_occurrences": total_occurrences,
            "paper_count": paper_count,
        }
        self.finished = True
        self._append_log(f"Proses selesai. {paper_count} artikel siap ditampilkan.")
        self.emit(self.snapshot(event="complete"))

    def fail(self, error):
        self.error = str(error)
        self._append_log(str(error))
        self.emit(self.snapshot(event="error", message=str(error)))


def _sse_payload(data):
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


@search_bp.route("/search-progress", methods=["GET"])
def search_progress():
    keyword = request.args.get("query", "").strip()
    if not keyword:
        return jsonify({
            "status": "error",
            "message": "Query tidak boleh kosong",
        }), 400

    selected_category = (
        request.args.get("kategori")
        or request.args.get("category")
        or ""
    ).strip()
    display_category = selected_category or "Semua kategori"

    target = request.args.get("target", request.args.get("top_k", default=10), type=int)
    target = max(1, min(int(target or 10), 50))
    year_start = request.args.get("year_start")
    year_end = request.args.get("year_end")
    jenis_artikel = request.args.get("jenis_artikel")
    jenis_analisis = request.args.get("jenis_analisis")
    jumlah_publikasi = request.args.get("jumlah_publikasi")
    jumlah_kemunculan = (
        request.args.get("jumlah_kemunculan")
        or request.args.get("jumlahKemunculan")
    )

    event_queue = queue.Queue()
    reporter = SearchProgressReporter(
        event_queue.put,
        keyword=keyword,
        category=display_category,
        target=target,
    )

    def run_pipeline():
        try:
            reporter.handle({
                "stage": "start",
                "event": "start",
                "message": "Menyiapkan proses pencarian...",
            })
            reporter.handle({
                "stage": "start",
                "event": "done",
                "message": "Pencarian dimulai dari dataset yang sudah tersedia",
            })

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
                progress_callback=reporter.handle,
            )
            reporter.complete(result)
        except Exception as error:
            reporter.fail(error)
        finally:
            event_queue.put(None)

    @stream_with_context
    def generate():
        worker = threading.Thread(target=run_pipeline, daemon=True)
        worker.start()
        while True:
            event = event_queue.get()
            if event is None:
                break
            yield _sse_payload(event)

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )

@search_bp.route("/search", methods=["GET"])
def search():
    query = request.args.get("query", "").strip()
    if not query:
        return jsonify({
            "status": "error",
            "message": "Query tidak boleh kosong",
        }), 400

    top_k = request.args.get("top_k", default=10, type=int)
    year_start = request.args.get("year_start")
    year_end = request.args.get("year_end")
    jenis_artikel = request.args.get("jenis_artikel")
    jenis_analisis = request.args.get("jenis_analisis")
    jumlah_publikasi = request.args.get("jumlah_publikasi")
    kategori = request.args.get("kategori")
    jumlah_kemunculan = (
        request.args.get("jumlah_kemunculan")
        or request.args.get("jumlahKemunculan")
    )

    try:
        result = search_articles(
            query=query,
            top_k=top_k,
            year_start=year_start,
            year_end=year_end,
            jenis_artikel=jenis_artikel,
            jenis_analisis=jenis_analisis,
            jumlah_kemunculan=jumlah_kemunculan,
            jumlah_publikasi=jumlah_publikasi,
            kategori=kategori,
        )
    except Exception as error:
        return jsonify({
            "status": "error",
            "message": str(error),
        }), 500

    return jsonify({
        "status": "success",
        "query": query,
        "total": result.get(
            "total_matched",
            len(result["articles"]),
        ),
        "total_matched": result.get(
            "total_matched",
            len(result["articles"]),
        ),
        "displayed_count": result.get(
            "displayed_count",
            len(result["articles"]),
        ),
        "total_occurrences": result["total_occurrences"],
        "paper_count": result["paper_count"],
        "data": result["articles"],
    })

@search_bp.route("/results")
def results():    
    result = get_cosine_catalog()
    return jsonify(result["articles"])

@search_bp.route("/cosine-results", methods=["GET"])
def cosine_results():
    result = get_cosine_catalog(
        query=request.args.get("query"),
        kategori=request.args.get("kategori") or request.args.get("category"),
        year_start=request.args.get("year_start"),
        year_end=request.args.get("year_end"),
        jenis_artikel=request.args.get("jenis_artikel"),
        sort_by=request.args.get("sort_by") or "query_rank",
    )

    return jsonify({
        "status": "success",
        "total": result["total"],
        "total_all": result["total_all"],
        "data": result["articles"],
        "queries": result["queries"],
        "categories": result["categories"],
    })

# @search_bp.route("/categories", methods=["GET"])  # /api/search/categories
# def categories():
#     return jsonify({
#         "status": "success",
#         "data": get_category_options(),
#     })

@search_bp.route("/stats", methods=["GET"])
def stats():
    return jsonify({
        "status": "success",
        "data": get_stats(),
    })

@search_bp.route("/categories", methods=["GET"])
def categories():
    return jsonify({
        "status": "success",
        "data": get_category_options(),
    })

@search_bp.route("/relation-types", methods=["GET"])
def relation_types():
    try:
        data = get_relation_type_options()
    except Exception as error:
        return jsonify({
            "status": "error",
            "message": str(error),
        }), 500

    return jsonify({
        "status": "success",
        "data": data,
    })

@search_bp.route("/detail/<int:article_id>", methods=["GET"])
def publication_detail(article_id):
    try:
        article = get_article_by_id(article_id)
    except Exception as error:
        return jsonify({
            "status": "error",
            "message": str(error),
        }), 500

    if not article:
        return jsonify({
            "status": "error",
            "message": "Artikel tidak ditemukan",
        }), 404

    return jsonify({
        "status": "success",
        "data": article,
    })
