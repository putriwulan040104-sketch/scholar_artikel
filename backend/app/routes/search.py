from app.search_engine import search_articles, get_category_options, get_cosine_catalog
from flask import Blueprint, jsonify, request

search_bp = Blueprint("search", __name__)

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

@search_bp.route("/categories", methods=["GET"])  # /api/search/categories
def categories():
    return jsonify({
        "status": "success",
        "data": get_category_options(),
    })

@search_bp.route("", methods=["GET"])  # /api/search
def search():
    query = request.args.get("query", "").strip()
    if not query:
        return jsonify({"status": "error", "message": "Query wajib diisi"}), 400

    top_k = request.args.get("top_k", 10, type=int)
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

    return jsonify({
        "status": "success",
        "total": result.get("total_matched", len(result["articles"])),
        "total_matched": result.get("total_matched", len(result["articles"])),
        "displayed_count": result.get("displayed_count", len(result["articles"])),
        "data": result["articles"],
        "total_occurrences": result["total_occurrences"],
        "paper_count": result["paper_count"],
    })
