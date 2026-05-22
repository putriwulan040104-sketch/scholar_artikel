from flask import Blueprint, jsonify, request 

from app.services.publication_service import process_articles
from app.search_engine import search_articles, get_stats

publication_bp = Blueprint(
    "publication",
    __name__
)


@publication_bp.route("/extract-publications", methods=["GET"])
def extract_publications():
    results = process_articles()
    return jsonify({
        "message": "Extraction completed",
        "results": results
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