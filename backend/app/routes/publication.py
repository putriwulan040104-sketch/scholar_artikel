from flask import Blueprint, jsonify, request
from app.services.citation.bibliographic_coupling_service import (
    BibliographicBuildInProgressError,
    build_bibliographic_coupling,
)
from app.services.citation.keyword_cooccurrence_service import (
    KeywordCooccurrenceBuildInProgressError,
    build_keyword_cooccurrence,
)
from app.services.citation.coauthorship_service import (
    CoauthorshipBuildInProgressError,
    build_coauthorship,
)
from app.services.citation.sna_service import (
    build_graph_payload,
    build_sna_metrics,
)
from app.services.processing.publication_service import (
    ReferenceRepairInProgressError,
    audit_reference_data,
    process_articles,
    repair_reference_data,
)

publication_bp = Blueprint("publication", __name__)

@publication_bp.route("/extract-publications", methods=["GET"])
def extract_publications():
    raw_ids = (request.args.get("ids") or "").strip()
    source_ids = None
    if raw_ids:
        source_ids = [
            int(token.strip())
            for token in raw_ids.split(",")
            if token.strip().isdigit()
        ]
        if not source_ids:
            return jsonify({
                "message": "Parameter ids tidak valid",
                "results": [],
            }), 400

    try:
        results = process_articles(source_ids=source_ids)
    except Exception as error:
        return jsonify({
            "message": "Extraction failed",
            "error": str(error),
            "results": [],
        }), 502

    return jsonify({
        "message": "Extraction completed",
        "ids": source_ids,
        "results": results,
    })


@publication_bp.route("/audit-references", methods=["GET"])
def audit_references():
    try:
        result = audit_reference_data()
    except Exception as error:
        return jsonify({
            "message": "Reference audit failed",
            "error": str(error),
        }), 502

    return jsonify({
        "message": "Reference audit completed",
        "result": result,
    })


@publication_bp.route("/repair-references", methods=["POST", "GET"])
def repair_references():
    raw_ids = (request.args.get("ids") or "").strip()
    source_ids = None
    if raw_ids:
        source_ids = [
            int(token.strip())
            for token in raw_ids.split(",")
            if token.strip().isdigit()
        ]
    limit = request.args.get("limit", type=int)

    try:
        result = repair_reference_data(
            source_ids=source_ids,
            limit=limit,
        )
    except ReferenceRepairInProgressError as error:
        return jsonify({"message": str(error)}), 409
    except Exception as error:
        return jsonify({
            "message": "Reference repair failed",
            "error": str(error),
        }), 502

    return jsonify({
        "message": "Reference repair completed",
        "result": result,
    })


@publication_bp.route(
    "/build-bibliographic-coupling",
    methods=["POST", "GET"],
)
def build_bibliographic_relations():
    limit = request.args.get("limit")
    min_shared = request.args.get(
        "min_shared",
        default=1,
        type=int,
    )
    min_shared = max(1, min(min_shared, 100))

    try:
        summary = build_bibliographic_coupling(
            limit=limit,
            min_shared=min_shared,
        )
    except BibliographicBuildInProgressError as error:
        return jsonify({"message": str(error)}), 409
    except Exception as error:
        return jsonify({
            "message": "Build bibliographic coupling failed",
            "error": str(error),
        }), 502

    return jsonify({
        "message": "Build bibliographic coupling completed",
        "summary": summary,
    })


@publication_bp.route(
    "/build-keyword-cooccurrence",
    methods=["POST", "GET"],
)
def build_keyword_relations():
    limit = request.args.get("limit", type=int)
    if limit is not None:
        limit = max(1, limit)
    min_shared = request.args.get(
        "min_shared",
        default=2,
        type=int,
    )
    min_shared = max(1, min(min_shared, 100))

    try:
        summary = build_keyword_cooccurrence(
            limit=limit,
            min_shared=min_shared,
        )
    except KeywordCooccurrenceBuildInProgressError as error:
        return jsonify({"message": str(error)}), 409
    except Exception as error:
        return jsonify({
            "message": "Build keyword co-occurrence failed",
            "error": str(error),
        }), 502

    return jsonify({
        "message": "Build keyword co-occurrence completed",
        "summary": summary,
    })


@publication_bp.route(
    "/build-co-authorship",
    methods=["POST", "GET"],
)
def build_coauthorship_relations():
    limit = request.args.get("limit", type=int)
    if limit is not None:
        limit = max(1, limit)
    min_shared = request.args.get(
        "min_shared",
        default=1,
        type=int,
    )
    min_shared = max(1, min(min_shared, 100))

    try:
        summary = build_coauthorship(
            limit=limit,
            min_shared=min_shared,
        )
    except CoauthorshipBuildInProgressError as error:
        return jsonify({"message": str(error)}), 409
    except Exception as error:
        return jsonify({
            "message": "Build co-authorship failed",
            "error": str(error),
        }), 502

    return jsonify({
        "message": "Build co-authorship completed",
        "summary": summary,
    })


@publication_bp.route("/sna-summary", methods=["GET"])
def sna_summary():
    top_n = request.args.get("top_n", default=10, type=int)
    top_n = max(1, min(top_n, 100))
    relation_type = (
        request.args.get("relation_type")
        or "bibliographic_coupling"
    ).strip()
    allowed_relation_types = {
        "bibliographic_coupling",
        "keyword_cooccurrence",
        "co_authorship",
    }
    if relation_type not in allowed_relation_types:
        return jsonify({
            "message": "Jenis relasi tidak valid",
            "allowed": sorted(allowed_relation_types),
        }), 400

    try:
        result = build_sna_metrics(
            top_n=top_n,
            relation_type=relation_type,
        )
    except Exception as error:
        return jsonify({
            "message": "Build SNA summary failed",
            "error": str(error),
        }), 502

    return jsonify({
        "message": "SNA summary generated",
        "result": result,
    })


@publication_bp.route("/graph-data", methods=["GET"])
def graph_data():
    try:
        raw_ids = (request.args.get("article_ids") or "").strip()
        relation_type = (
            request.args.get("relation_type")
            or "bibliographic_coupling"
        ).strip()
        allowed_relation_types = {
            "bibliographic_coupling",
            "keyword_cooccurrence",
            "co_authorship",
        }
        if relation_type not in allowed_relation_types:
            return jsonify({
                "message": "Jenis relasi tidak valid",
                "allowed": sorted(allowed_relation_types),
            }), 400

        article_ids = None
        if raw_ids:
            parsed = []
            for token in raw_ids.split(","):
                token = token.strip()
                if not token:
                    continue
                try:
                    parsed.append(int(token))
                except ValueError:
                    continue
            article_ids = parsed or None

        payload = build_graph_payload(
            article_ids=article_ids,
            relation_type=relation_type,
        )
    except Exception as error:
        return jsonify({
            "message": "Build graph data failed",
            "error": str(error),
        }), 502

    return jsonify({
        "message": "Graph data generated",
        "result": payload,
    })
