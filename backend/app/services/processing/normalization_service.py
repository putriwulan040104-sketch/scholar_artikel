import re
from app.utils.cleaner import (
    clean_text,
    lowercase_text
)

# NORMALISASI KEYWORDS
def normalize_keywords(keywords):
    if not keywords:
        return []

    normalized = []
    seen = set()

    for keyword in keywords:
        keyword = clean_text(keyword)
        keyword = lowercase_text(keyword)
        if not keyword or keyword in seen:
            continue
        seen.add(keyword)
        normalized.append(keyword)

    return normalized

# NORMALISASI REFERENCE
def normalize_reference(reference):
    if not reference:
        return []

    expanded = []
    for ref in reference:
        ref = str(ref)
        parts = re.split(
            r"\s+-\s+(?=(?:[A-Z0-9\"']|COVID-19))",
            ref,
        )
        if len(parts) > 1:
            expanded.extend(parts)
        else:
            expanded.append(ref)

    frontiers_expanded = []
    for ref in expanded:
        if len(ref) > 2000:
            parts = re.split(
                r"(?<=\d)\s+(?=[A-Z][a-zÀ-ÿ?-]{2,}[A-Z]\.)",
                ref,
            )
            if len(parts) > 1:
                frontiers_expanded.extend(parts)
                continue
        frontiers_expanded.append(ref)

    normalized = []
    seen = set()

    for ref in frontiers_expanded:
        ref = clean_text(ref)
        ref = re.sub(r"\s+", " ", ref)
        if not ref:
            continue
        key = ref.lower()
        if key in seen:
            continue
        seen.add(key)
        normalized.append(ref)

    return normalized
