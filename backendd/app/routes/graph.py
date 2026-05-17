from fastapi import APIRouter
from ..services.graph_service import build_graph
from ..services.citation_builder_service import build_citations_from_pdfs

router = APIRouter(prefix="/graph", tags=["graph"])

@router.get("")
async def get_graph():
    return build_graph()


@router.get("/build")
async def build_graph_from_pdf(limit: int = 0):
    return build_citations_from_pdfs(limit=limit)
