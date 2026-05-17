from pydantic import BaseModel
from typing import List, Optional

class PublicationBase(BaseModel):
    title: str
    authors: List[str]
    year: int
    citation_count: int
    keywords: Optional[List[str]] = None
    abstract: Optional[str] = None

class Publication(PublicationBase):
    id: str

class CitationEdge(BaseModel):
    citing_id: str
    cited_id: str

class PublicationWithCitations(Publication):
    cited_by: List[Publication] = []   # artikel yang menyitasi
    references: List[Publication] = []  # artikel yang disitasi