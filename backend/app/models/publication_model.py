from app.utils.cleaner import clean_text

import app.services.extraction_service as extractor

import app.services.normalization_service \
    as normalizer


# ==========================================
# TITLE FROM PDF
# ==========================================

def extract_title_from_text(text):

    lines = text.split("\n")

    for line in lines[:20]:

        line = clean_text(line)

        if line and len(line) > 15:

            if "abstract" not in line.lower():
                return line

    return None


# ==========================================
# AUTHORS FROM PDF
# ==========================================

def extract_authors_from_text(text):

    lines = text.split("\n")

    authors = []

    for line in lines[1:10]:

        line = clean_text(line)

        if not line:
            continue

        if len(line) < 100:
            authors.append(line)

    return authors[:5]


# ==========================================
# BUILD PUBLICATION
# ==========================================

def build_publication(
    article,
    metadata,
    content
):

    # ======================================
    # URL
    # ======================================

    article_url = article.get("url")

    pdf_url = article.get("pdf_url")

    # ======================================
    # TITLE
    # ======================================

    title = article.get("title")

    if not title:

        if metadata and metadata.title:

            title = clean_text(
                metadata.title
            )

        else:

            title = extract_title_from_text(
                content
            )

    # ======================================
    # AUTHORS
    # ======================================

    authors = article.get("authors")

    if not authors:

        if metadata and metadata.author:

            authors = metadata.author

        else:

            authors = extract_authors_from_text(
                content
            )

    # ======================================
    # YEAR
    # ======================================

    year = article.get("year")

    if not year:
        year = extractor.extract_year(
            content
        )

    # ======================================
    # JOURNAL
    # ======================================

    journal = article.get("source")

    if not journal:

        journal = (
            metadata.sitename
            if metadata and metadata.sitename
            else None
        )

    # ======================================
    # EXTRACTION
    # ======================================

    keywords = extractor.extract_keywords(
        content
    )

    reference_list = extractor.extract_reference(
        content
    )

    doi = extractor.extract_doi(
        content
    )

    # ======================================
    # NORMALIZATION
    # ======================================

    return {

        "article_url":
            article_url,

        "pdf_url":
            pdf_url,

        "title":
            normalizer.normalize_title(
                title
            ),

        "authors":
            normalizer.normalize_authors(
                authors
            ),

        "keywords":
            normalizer.normalize_keywords(
                keywords
            ),

        "reference_list":
            normalizer.normalize_reference(
                reference_list
            ),

        "doi":
            normalizer.normalize_doi(
                doi
            ),

        "journal":
            clean_text(journal),

        "year":
            year,

        "raw_text":
            content[:50000]
    }