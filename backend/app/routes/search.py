from flask import Blueprint, jsonify, request

from app.search_engine import (
    get_article_by_id,
    get_category_options,
    get_relation_type_options,
    get_stats,
    search_articles,
)


search_bp = Blueprint("search", __name__)


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
