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

from app.search_engine import search_articles, get_stats

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
        payload = build_graph_payload()
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
    query      = request.args.get('query', '').strip()
    top_k      = int(request.args.get('top_k', 10))
    year_start = request.args.get('year_start')
    year_end   = request.args.get('year_end')

    if not query:
        return jsonify({'status': 'error',
                        'message': 'Query tidak boleh kosong'}), 400
    try:
        results = search_articles(query, top_k, year_start, year_end)
        return jsonify({'status': 'success', 'query': query,
                        'total': len(results), 'data': results})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@publication_bp.route("/stats", methods=["GET"])
def stats():
    return jsonify({'status': 'success', 'data': get_stats()})
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