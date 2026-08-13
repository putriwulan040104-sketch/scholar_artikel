import re
from app.utils.cleaner import (
    clean_text,
    lowercase_text
)

# mendeteksi apakah suatu teks merupakan awal dari referensi ilmiah
def _starts_like_reference(ref):
    ref = re.sub(r"\s+", " ", str(ref or "")).strip() # membersihkan spasi berlebih
    if len(ref) < 20:
        return False

    # mengecek referensi diawali dengan format nomor
    if re.match(r"^(?:[-*•]\s+|\[\d+\]|\(\d+\)|\d{1,3}[\.)]\s+)", ref):
        return True

    has_year = bool(re.search(r"\b(?:19|20)\d{2}[a-z]?\b", ref))
    author_part = ref[:180]
    if has_year:
        year_match = re.search(r"\b(?:19|20)\d{2}[a-z]?\b", ref)
        author_part = ref[:year_match.start()] if year_match else author_part

    author_part = re.sub(
        r"^\s*(?:[-*•]\s+|\[\d+\]|\(\d+\)|\d{1,3}[\.)]\s*)",
        "",
        author_part,
    ).strip(" ,.;:")

    author_patterns = [
        r"^[A-Z][A-Za-z'`-]{1,},\s*(?:[A-Z]\.?\s*){1,5}",
        r"^(?:[A-Z]\.?\s*){1,5}\s*[A-Z][A-Za-z'`-]{1,}\s*,",
        r"^[A-Z][A-Za-z'`-]{1,}\s+et\s+al\.?",
        r"^[A-Z][A-Za-z'`-]{1,}\s+(?:and|&)\s+[A-Z][A-Za-z'`-]{1,}",
    ]
    return has_year and any(re.search(pattern, author_part) for pattern in author_patterns)

# memisahkan dua/lebih referensi yang tertulis dalam satu baris
def _split_joined_references(ref):
    parts = re.split(r"\s+-\s+", str(ref or ""))
    if len(parts) <= 1:
        return [ref]

    rebuilt = []
    current = parts[0]
    for part in parts[1:]:
        if _starts_like_reference(part):
            rebuilt.append(current)
            current = part
        else:
            current = f"{current} - {part}"

    rebuilt.append(current)
    return rebuilt

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
        expanded.extend(_split_joined_references(ref))

    frontiers_expanded = []
    for ref in expanded:
        if len(ref) > 400:
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
