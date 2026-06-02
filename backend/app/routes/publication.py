from flask import Blueprint, jsonify, request
from app.services.processing.publication_service import (
    process_articles
)
from app.services.citation.citation_relation_service import (
    build_citation_relations
)
from app.services.citation.sna_service import (
    build_sna_metrics,
    build_graph_payload,
)
from flask import Blueprint, jsonify, request 

from app.search_engine import search_articles, get_category_options, get_stats

publication_bp = Blueprint(
    "publication", __name__
)


@publication_bp.route("/extract-publications", methods=["GET"])
def extract_publications():
    try:
        results = process_articles()
    except Exception as e:
        return jsonify({
            "message": "Extraction failed",
            "error": str(e),
            "results": []
        }), 502

    results = process_articles()
    return jsonify({
        "message": "Extraction completed",
        "results": results
    })


@publication_bp.route(
    "/build-citations",
    methods=["POST", "GET"]
)
def build_citations():
    limit = request.args.get("limit")

    try:
        summary = build_citation_relations(limit=limit)
    except Exception as e:
        return jsonify({
            "message": "Build citation relations failed",
            "error": str(e)
        }), 502

    return jsonify({
        "message": "Build citation relations completed",
        "summary": summary
    })


@publication_bp.route(
    "/sna-summary",
    methods=["GET"]
)
def sna_summary():
    top_n = request.args.get("top_n", default=10, type=int)
    top_n = max(1, min(top_n, 100))

    try:
        result = build_sna_metrics(top_n=top_n)
    except Exception as e:
        return jsonify({
            "message": "Build SNA summary failed",
            "error": str(e)
        }), 502

    return jsonify({
        "message": "SNA summary generated",
        "result": result
    })


@publication_bp.route(
    "/graph-data",
    methods=["GET"]
)
def graph_data():
    try:
        raw_ids = (request.args.get("article_ids") or "").strip()
        article_ids = None
        if raw_ids:
            parsed = []
            for token in raw_ids.split(","):
                token = token.strip()
                if not token:
                    continue
                try:
                    parsed.append(int(token))
                except Exception:
                    continue
            article_ids = parsed if parsed else None

        payload = build_graph_payload(article_ids=article_ids)
    except Exception as e:
        return jsonify({
            "message": "Build graph data failed",
            "error": str(e)
        }), 502

    return jsonify({
        "message": "Graph data generated",
        "result": payload
    })

@publication_bp.route("/search", methods=["GET"])
def search():
    query             = request.args.get('query', '').strip()
    top_k             = int(request.args.get('top_k', 10))
    year_start        = request.args.get('year_start')
    year_end          = request.args.get('year_end')
    jenis_artikel     = request.args.get('jenis_artikel')
    jenis_analisis    = request.args.get('jenis_analisis')
    jumlah_kemunculan = request.args.get('jumlah_kemunculan')
    jumlah_publikasi  = request.args.get('jumlah_publikasi')
    kategori          = request.args.get('kategori')

    if not query:
        return jsonify({'status': 'error', 'message': 'Query tidak boleh kosong'}), 400

    try:
        result = search_articles(
            query,
            top_k,
            year_start,
            year_end,
            jenis_artikel     = jenis_artikel,
            jenis_analisis    = jenis_analisis,
            jumlah_publikasi  = jumlah_publikasi,
            jumlah_kemunculan = jumlah_kemunculan,
            kategori          = kategori,
        )

        # ← result sekarang dict, bukan list
        return jsonify({
            'status'           : 'success',
            'query'            : query,
            'total'            : result.get("total_matched", len(result["articles"])),
            'total_matched'    : result.get("total_matched", len(result["articles"])),
            'displayed_count'  : result.get("displayed_count", len(result["articles"])),
            'total_occurrences': result["total_occurrences"],
            'paper_count'      : result["paper_count"],
            'data'             : result["articles"],  # ← ambil dari key "articles"
        })

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@publication_bp.route("/stats", methods=["GET"])
def stats():
    return jsonify({'status': 'success', 'data': get_stats()})


@publication_bp.route("/categories", methods=["GET"])
def publication_categories():
    return jsonify({
        "status": "success",
        "data": get_category_options(),
    })


from app.search_engine import search_articles, get_stats, get_article_by_id  # ← tambah import

@publication_bp.route("/detail/<int:id>", methods=["GET"])  # ← ganti nama route
def get_publication_detail(id):
    try:
        article = get_article_by_id(id)
        
        if not article:
            return jsonify({
                "status" : "error",
                "message": "Artikel tidak ditemukan"
            }), 404
            
        return jsonify({
            "status": "success",
            "data"  : article
        })
    except Exception as e:
        return jsonify({
            "status" : "error",
            "message": str(e)
        }), 500
