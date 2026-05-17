from flask import Blueprint, jsonify

from app.services.publication_service import (
    process_articles
)

publication_bp = Blueprint(
    "publication",
    __name__
)


@publication_bp.route(
    "/extract-publications",
    methods=["GET"]
)
def extract_publications():

    results = process_articles()

    return jsonify({
        "message": "Extraction completed",
        "results": results
    })