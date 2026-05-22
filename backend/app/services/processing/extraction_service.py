import re
from app.utils.cleaner import clean_text

# INTERNAL HELPERS
def _looks_like_reference_entry(ref):
    if not ref:
        return False

    ref = re.sub(
        r"\s+",
        " ",
        ref
    ).strip()

    if len(ref) < 20:
        return False

    lower = ref.lower()

    has_year = bool(
        re.search(r"(19|20)\d{2}", ref)
    )
    has_doi = bool(
        re.search(
            r"\b10\.\d{4,9}/[-._;()/:A-Z0-9]+\b",
            ref,
            re.I
        )
    )

    has_url = (
        "http://" in lower
        or "https://" in lower
        or "www." in lower
    )

    has_citation_marker = bool(
        re.match(
            r"^\s*(\[\d{1,3}\]|\(\d{1,3}\)|\d{1,3}[\.\)]|•|-|\*)\s*",
            ref
        )
    )
    has_author_pattern = bool(
        re.search(
            r"[A-Z][a-z]+,\s*[A-Z]",
            ref
        )
    )

    if has_doi or has_url or has_citation_marker:
        return True
    if has_year and (
        has_author_pattern
        or len(ref.split()) >= 6
    ):
        return True

    return False


def _normalize_pdf_artifacts(text):
    if not text:
        return ""

    # Common mojibake from PDF extraction.
    replacements = {
        "â€¢": "•",
        "Ã¢â‚¬Â¢": "•",
        "Ã¢â‚¬â€": "-",
        "Ã¢â‚¬â€œ": "-",
        "\ufb01": "fi",
        "\ufb02": "fl",
    }

    out = text
    for bad, good in replacements.items():
        out = out.replace(bad, good)

    return out

# DOI
def extract_doi(text):
    if not text:
        return None

    first_part = text[:2000]

    pattern = (
        r"\b10\.\d{4,9}"
        r"/[-._;()/:A-Z0-9]+\b"
    )

    matches = re.findall(
        pattern,
        first_part,
        re.I
    )

    if matches:
        return matches[0]

    return None

# KEYWORDS
def extract_keywords(text):
    patterns = [
        r"(?:keywords?|index terms?|kata kunci)"
        r"\s*[:\-]?\s*([^\n]+)"
    ]

    blacklist = [
        "introduction",
        "abstract",
        "references"
    ]

    for pattern in patterns:
        match = re.search(
            pattern,
            text,
            re.I
        )

        if not match:
            continue
        keyword_text = match.group(1)
        keywords = re.split(
            r",|;|\||â€¢|â€”|â€“",
            keyword_text
        )

        cleaned = []

        for k in keywords:
            k = clean_text(k)

            if not k:
                continue
            if len(k) > 40:
                continue
            if any(
                b in k.lower()
                for b in blacklist
            ):
                continue
            cleaned.append(k)

        if cleaned:
            return list(dict.fromkeys(cleaned))

    return []

# REFERENCES
def extract_reference(text):
    if not text:
            return []

    text = _normalize_pdf_artifacts(text)

    patterns = [
        r"\breferences\b",
        r"\breference\b",
        r"\bbibliography\b",
        r"\bworks cited\b",
        r"\bdaftar pustaka\b",
        r"\breferensi\b",
        r"r\s*e\s*f\s*e\s*r\s*e\s*n\s*c\s*e\s*s",
    ]

    reference_text = None

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.I
        )

        if match:
            reference_text = text[
                match.end():
            ]
            break

    if not reference_text:
        return []
    
    stop_patterns = [
        r"\bappendix\b",
        r"\backnowledg",
        r"\bauthor biography\b"
    ]

    for stop in stop_patterns:
        stop_match = re.search(
            stop,
            reference_text,
            re.I
        )

        if stop_match:
            reference_text = reference_text[
                :stop_match.start()
            ]

    reference_text = re.sub(
        r"\n+",
        "\n",
        reference_text
    )

    # Normalized lines and remove pure page numbers.
    reference_text = re.sub(r"\n\s*\d+\s*\n", "\n", reference_text)

    lines = reference_text.split("\n")
    references = []
    current_ref = ""

    for line in lines:
        line = clean_text(line)

        if not line:
            continue

        is_new_ref = re.match(
            r"""
            ^
            (
                \[\d+\]|
                \(\d+\)|
                \d+[\.\)]|
                [A-Z][a-z]+,\s*[A-Z]|
                [A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2}\s*\(\d{4}\)
            )
            """,
            line,
            re.X
        )

        if len(line) < 5:
            continue
        if is_new_ref:
            if current_ref:
                references.append(
                    current_ref.strip()
                )

            current_ref = line

        else:
            current_ref += " " + line

    if current_ref:
        references.append(
            current_ref.strip()
        )

    # Fallback heuristic: if marker-based parsing fails, rebuild candidates
    # from dense lines that look like citations.
    if len(references) <= 1:
        dense = []
        for line in lines:
            line = clean_text(line)
            if not line:
                continue
            if len(line) < 20:
                continue
            dense.append(line)

        rebuilt = []
        buf = ""
        for line in dense:
            starts_new = bool(
                re.match(
                    r"^\s*(\[\d+\]|\(\d+\)|\d+[\.\)]|[A-Z][a-z]+,\s*[A-Z])",
                    line
                )
            )

            if starts_new and buf:
                rebuilt.append(buf.strip())
                buf = line
            else:
                if not buf:
                    buf = line
                else:
                    buf += " " + line

        if buf:
            rebuilt.append(buf.strip())

        if rebuilt:
            references = rebuilt

    clean_refs = []
    seen = set()

    for ref in references:
        ref = re.sub(
            r"\s+",
            " ",
            ref
        )

        if len(ref) < 30:
            continue
        if not _looks_like_reference_entry(
            ref
        ):
            continue

        normalized = ref.lower()

        if normalized in seen:
            continue

        seen.add(normalized)
        clean_refs.append(ref)

    return clean_refs

# YEAR
def extract_year(text):
    years = re.findall(
        r"(?:19|20)\d{2}",
        text
    )

    if years:
        try:
            return int(years[0])
        except:
            return None

    return None
