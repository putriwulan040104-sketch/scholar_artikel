from fastapi import APIRouter, Query, HTTPException
from typing import Optional
from ..database import supabase

router = APIRouter(prefix="/publications", tags=["publications"])

# GRAPH
@router.get("/graph")
async def get_full_graph():
    edges_res = supabase.table("citations").select("citing_id,cited_id").execute()
    pubs_res = supabase.table("scholar_articles").select("id,title,year").execute()

    return {
        "nodes": pubs_res.data or [],
        "edges": [
            {"source": e["citing_id"], "target": e["cited_id"]}
            for e in (edges_res.data or [])
        ]
    }

# SEARCH
@router.get("/search")
async def search_publications(
    q: Optional[str] = None,
    year_from: Optional[int] = None,
    year_to: Optional[int] = None,
    min_citations: Optional[int] = None,
    limit: int = Query(20, ge=1, le=100)
):

    query = supabase.table("scholar_articles").select("*")

    if q:
        query = query.or_(
            f"title.ilike.%{q}%,abstract.ilike.%{q}%,authors.ilike.%{q}%"
        )

    if year_from:
        query = query.gte("year", year_from)

    if year_to:
        query = query.lte("year", year_to)

    if min_citations:
        query = query.gte("citations", min_citations)

    res = query.limit(limit).execute()

    return {
        "data": res.data or [],
        "count": len(res.data or [])
    }

#LIST
@router.get("")
async def list_publications(limit: int = Query(50, ge=1, le=500)):

    res = (
        supabase
        .table("scholar_articles")
        .select("*")
        .order("year", desc=True)
        .limit(limit)
        .execute()
    )

    return {
        "count": len(res.data or []),
        "data": res.data or []
    }

# DETAIL
@router.get("/{pub_id}")
async def get_publication_detail(pub_id: int):

    res = (
        supabase
        .table("scholar_articles")
        .select("*")
        .eq("id", pub_id)
        .single()
        .execute()
    )

    if not res.data:
        raise HTTPException(404, "Publication not found")

    return res.data
