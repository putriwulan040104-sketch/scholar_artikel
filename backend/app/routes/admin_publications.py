from flask import Blueprint, jsonify, request

from app.services.admin_publication_service import (
    delete_admin_publication,
    get_admin_publications,
    update_admin_publication,
)


admin_publications_bp = Blueprint("admin_publications", __name__)


def _get_bearer_token():
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return ""
    return auth_header.replace("Bearer ", "", 1).strip()


def _response(result, success_code=200):
    if result.get("status") == "error":
        return jsonify(result), result.get("status_code", 400)
    return jsonify(result), success_code


@admin_publications_bp.route("/admin/publications", methods=["GET"])
def list_publications():
    return _response(get_admin_publications(_get_bearer_token()))


@admin_publications_bp.route(
    "/admin/publications/<int:publication_id>",
    methods=["PUT"],
)
def update_publication(publication_id):
    return _response(
        update_admin_publication(
            _get_bearer_token(),
            publication_id,
            request.get_json(silent=True) or {},
        )
    )


@admin_publications_bp.route(
    "/admin/publications/<int:publication_id>",
    methods=["DELETE"],
)
def delete_publication(publication_id):
    return _response(
        delete_admin_publication(_get_bearer_token(), publication_id)
    )
