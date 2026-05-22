import re
import app.services.processing.extraction_service as extractor
import app.services.processing.normalization_service as normalizer
from app.utils.cleaner import clean_text

# TITLE FROM PDF
def extract_title_from_text(text):
    lines = text.split("\n")

    for line in lines[:20]:
        line = clean_text(line)

        if not line:
            continue
        if len(line) < 15:
            continue

        blacklist = [
            "abstract",
            "introduction",
            "keywords",
            "references"
        ]

        if any(
            b in line.lower()
            for b in blacklist
        ):
            continue

        return line

    return None

# AUTHORS FROM PDF
def extract_authors_from_text(text):
    lines = text.split("\n")
    authors = []

    for line in lines[1:15]:
        line = clean_text(line)

        if not line:
            continue
        if len(line) > 100:
            continue
        if "university" in line.lower():
            continue
        if "department" in line.lower():
            continue
        authors.append(line)

    return authors[:5]

# CLEAN PDF TEXT
def clean_pdf_text(text):
    if not text:
        return ""

    text = text.replace("\x0c", "\n")
    text = re.sub( r"-\s*\n\s*", "", text)
    text = re.sub(r"\n{2,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(
        r"R\s*E\s*F\s*E\s*R\s*E\s*N\s*C\s*E\s*S",
        "REFERENCES", text, flags=re.I
    )
    text = re.sub(
        r"K\s*E\s*Y\s*W\s*O\s*R\s*D\s*S",
        "KEYWORDS", text, flags=re.I
    )

    return text

# BUILD PUBLICATION
def build_publication(
    article,
    metadata,
    content,
    html_keywords=None,
    html_references=None,
    html_doi=None
):

    content = clean_pdf_text(content)
    article_url = article.get("url")
    pdf_url = article.get("pdf_url")
    title = article.get("title")

    if not title:
        if metadata and metadata.title:
            title = clean_text(metadata.title)

        else:
            title = extract_title_from_text(content)

    # AUTHORS
    authors = article.get("authors")
    if not authors:
        if metadata and metadata.author:
            authors = metadata.author

        else:
            authors = extract_authors_from_text(content)

    # YEAR
    year = article.get("year")
    if not year:
        year = extractor.extract_year(content)

    # JOURNAL
    journal = article.get("source")
    if not journal:
        if metadata and metadata.sitename:
            journal = metadata.sitename

    # EXTRACTION
    keywords = extractor.extract_keywords(
        content
    )
    reference_list = extractor.extract_reference(
        content
    )
    doi = None

    # DOI dari metadata
    if metadata and hasattr(metadata, "doi"):
        doi = metadata.doi

    # DOI dari text
    if not doi:
        doi = extractor.extract_doi(content)

    # DOI fallback HTML
    if not doi and html_doi:
        doi = html_doi

    # KEYWORDS fallback HTML
    if (
        not keywords
        and
        html_keywords
    ):
        keywords = html_keywords

    # REFERENCES fallback HTML
    if (
        not reference_list
        and
        html_references
    ):
        reference_list = html_references

    # NORMALIZATION
    return {
        "article_id": article.get("id"),
        "article_url": article_url,
        "pdf_url": pdf_url,
        "title":
            normalizer.normalize_title(title),
        "authors":
            normalizer.normalize_authors(authors),
        "keywords":
            normalizer.normalize_keywords(keywords),
        "reference_list":
            normalizer.normalize_reference(reference_list),
        "doi": normalizer.normalize_doi(doi),
        "journal": clean_text(journal),
        "year": year,
        "raw_text": content[:50000]
    }
