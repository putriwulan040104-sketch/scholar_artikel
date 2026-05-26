import re
from app.utils.cleaner import (
    clean_text,
    lowercase_text
)

# NORMALISASI TITLE
def normalize_title(title):
    if not title:
        return None

    title = clean_text(title)
    title = lowercase_text(title)

    return title.title()

# NORMALISASI AUTHORS
def normalize_authors(authors):
    if not authors:
        return []
    if isinstance(authors, str):
        authors = [authors]

    normalized = []

    for author in authors:
        author = clean_text(author)
        author = re.sub(r"\d+", "", author)
        author = re.sub(r"[^\w\s.,]", "", author)
        author = lowercase_text(author)
        normalized.append(author.title())

    return list(set(normalized))

# NORMALISASI KEYWORDS
def normalize_keywords(keywords):
    if not keywords:
        return []

    normalized = []

    for keyword in keywords:
        keyword = clean_text(keyword)
        keyword = lowercase_text(keyword)
        normalized.append(keyword)

    return list(set(normalized))

# NORMALISASI REFERENCE
def normalize_reference(reference):
    if not reference:
        return []

    normalized = []

    for ref in reference:
        ref = clean_text(ref)
        ref = re.sub(r"\s+", " ", ref)
        normalized.append(ref)

    return normalized

# NORMALISASI DOI
def normalize_doi(doi):
    if not doi:
        return None

    return doi.lower().strip()