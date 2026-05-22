from flask import Blueprint, jsonify
from app.services.pipeline.publication_service import (
    process_articles
)

publication_bp = Blueprint(
    "publication", __name__
)


@publication_bp.route(
    "/extract-publications",
    methods=["GET"]
)
def extract_publications():
    try:
        results = process_articles()
    except Exception as e:
        return jsonify({
            "message": "Extraction failed",
            "error": str(e),
            "results": []
        }), 502

    return jsonify({
        "message": "Extraction completed",
        "results": results
    })
