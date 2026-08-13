import re
from collections import Counter
from app.utils.cleaner import clean_text

# INTERNAL HELPERS
def _looks_like_reference_entry(ref):
    if not ref:
        return False

    ref = re.sub(r"\s+", " ", ref).strip()

    if len(ref) < 20:
        return False

    lower = ref.lower()
    has_year = bool(re.search(r"(19|20)\d{2}", ref))
    has_doi = bool(
        re.search(r"\b10\.\d{4,9}/[-._;()/:A-Z0-9]+\b", ref, re.I)
    )
    has_url = (
        "http://" in lower
        or "https://" in lower
        or "www." in lower
    )
    has_citation_marker = bool(
        re.match(
            r"^\s*(\[\d{1,3}\]|\(\d{1,3}\)|\d{1,3}[\.\)]|•|-|\*)\s*", ref)
    )
    has_author_pattern = _has_reference_author_pattern(ref)

    if has_doi or has_url or has_citation_marker:
        return True
    if has_year and has_author_pattern:
        return True
    if has_author_pattern and len(ref.split()) >= 5:
        return True

    return False


def _has_author_year_pattern(ref):
    if not ref:
        return False

    ref = re.sub(r"\s+", " ", str(ref)).strip()
    year_match = re.search(r"\b(?:19|20)\d{2}[a-z]?\b", ref)
    if not year_match:
        return False

    author_part = ref[:year_match.start()]
    author_part = re.sub(
        r"^\s*(?:[-*â€¢]\s+|\[\d+\]|\(\d+\)|\d+[\.\)])\s*",
        "",
        author_part,
    ).strip(" ,.;:")

    if not author_part or len(author_part) > 180:
        return False

    author_patterns = [
        r"\b[A-Z][A-Za-z'`-]{1,},\s*(?:[A-Z]\.?\s*){1,5}",
        r"\b[A-Z][A-Za-z'`-]{1,}\s+(?:[A-Z]\.?\s*){1,5}",
        r"\b(?:[A-Z]\.?\s*){1,5}[A-Z][A-Za-z'`-]{1,}",
        r"\b[A-Z][A-Za-z'`-]{1,}\s+et\s+al\.?",
        r"\b[A-Z][A-Za-z'`-]{1,}\s+(?:and|&)\s+"
        r"[A-Z][A-Za-z'`-]{1,}",
    ]

    return any(
        re.search(pattern, author_part)
        for pattern in author_patterns
    )

# menghapus nomor referensi di depan text
def _strip_reference_marker(ref):
    return re.sub(
        r"^\s*(?:[-*â€¢Ã¢â‚¬Â¢]\s+|\[\d+\]|\(\d+\)|\d+[\.\)])\s*",
        "", str(ref or ""),
    ).strip()

# mengenali apakah bagian awal merupakan nama penulis
def _has_reference_author_pattern(ref):
    if not ref:
        return False

    ref = re.sub(r"\s+", " ", str(ref)).strip()
    year_match = re.search(r"\b(?:19|20)\d{2}[a-z]?\b", ref)
    author_part = ref[:year_match.start()] if year_match else ref[:180]
    author_part = _strip_reference_marker(author_part).strip(" ,.;:")

    if not author_part or len(author_part) > 180:
        return False

    author_patterns = [
        r"^[A-Z][A-Za-z'`-]{1,},\s*(?:[A-Z]\.?\s*){1,5}",
        r"^(?:[A-Z]\.?\s*){1,5}\s*[A-Z][A-Za-z'`-]{1,}\s*,",
        r"^[A-Z][A-Za-z'`-]{1,}\s+(?:[A-Z]\.?\s*){1,5}\s*,",
        r"^[A-Z][A-Za-z'`-]{1,}\s+et\s+al\.?",
        r"^[A-Z][A-Za-z'`-]{1,}\s+(?:and|&)\s+"
        r"[A-Z][A-Za-z'`-]{1,}",
    ]

    return any(
        re.search(pattern, author_part)
        for pattern in author_patterns
    )


def _starts_like_reference_entry(ref):
    if re.match(r"^\s*(?:[-*â€¢]\s+|\[\d+\]|\(\d+\)|\d+[\.\)])", ref):
        return True

    return _has_reference_author_pattern(ref)

#  normalisasi karakter aneh
def _normalize_pdf_artifacts(text):
    if not text:
        return ""

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

# KEYWORDS dengan heading
def _extract_keywords_legacy(text):
    patterns = [
        r"^[ \t]*(?:keywords?|key\s+words?|index terms?|kata kunci|"
        r"additional\s+(?:key\s+words?|keywords?)\s+and\s+phrases)"
        r"[ \t]*(?::|[-\u2013\u2014])[ \t]*([^\n]+)$",
        r"^[ \t]*(?:keywords?|key\s+words?|index terms?|kata kunci|"
        r"additional\s+(?:key\s+words?|keywords?)\s+and\s+phrases)"
        r"[ \t]*:?[ \t]*$\s*^([^\n]{2,300})$",
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
            re.I | re.M
        )

        if not match:
            continue
        keyword_text = match.group(1)
        keywords = re.split(r",|;|\||â€¢|â€”|â€“", keyword_text)

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


def extract_keywords(text):
    if not text:
        return []

    text = _normalize_pdf_artifacts(text)
    lines = text.splitlines()
    heading_pattern = re.compile(
        r"^\s*(keywords?|key\s+words?|index\s+terms?|kata\s+kunci|"
        r"additional\s+(?:key\s+words?|keywords?)\s+and\s+phrases)\s*"
        r"(?:(:|[-\u2013\u2014])\s*)?(.*)\s*$",
        re.I,
    )
    stop_pattern = re.compile(
        r"^(?:(?:\d+(?:\.\d+)*)\.?\s+)?"
        r"(?:abstract|introduction|background|references|"
        r"ccs concepts|acm reference format|"
        r"jel classification|acknowledg(?:e)?ments?|"
        r"correspondence|article history)\b",
        re.I,
    )

    for index, raw_line in enumerate(lines):
        match = heading_pattern.match(raw_line)
        if not match:
            continue

        label = match.group(1)
        separator = match.group(2)
        remainder = (match.group(3) or "").strip()

        if remainder and not separator and label != label.upper():
            continue

        keyword_lines = []
        if remainder:
            keyword_lines.append(remainder)

        for following_line in lines[index + 1:index + 31]:
            candidate = following_line.strip()
            if not candidate:
                if keyword_lines:
                    break
                continue
            if stop_pattern.match(candidate):
                break
            if heading_pattern.match(candidate):
                break
            if len(candidate) > 200:
                break
            candidate = re.sub(
                r"^\s*(?:[-*•▪◦]|\d+[\.)])\s*",
                "",
                candidate,
            ).strip()
            if candidate:
                keyword_lines.append(candidate)

        cleaned = []
        for keyword_line in keyword_lines:
            for keyword in re.split(r"\s*(?:,|;|\|)\s*", keyword_line):
                keyword = clean_text(keyword).strip(" -–—.,;:")
                if not keyword:
                    continue
                if len(keyword) > 80:
                    continue
                if stop_pattern.match(keyword):
                    continue
                cleaned.append(keyword)

        if cleaned:
            return list(dict.fromkeys(cleaned))
    
    result = _extract_keywords_legacy(text)
    return result

# REFERENCES
def extract_reference(text):
    if not text:
            return []

    text = _normalize_pdf_artifacts(text)

    heading_patterns = [
        r"references?",
        r"bibliography",
        r"works\s+cited",
        r"daftar\s+pustaka",
        r"referensi",
        r"r\s*e\s*f\s*e\s*r\s*e\s*n\s*c\s*e\s*s",
    ]

    heading_matches = []
    for pattern in heading_patterns:
        heading_matches.extend(
            re.finditer(
                rf"(?im)^[ \t]*(?:\d+[.)]?[ \t]+)?{pattern}"
                r"[ \t]*[:.]?[ \t]*$", text,
            )
        )

    reference_text = None
    if heading_matches:
        heading_match = max(
            heading_matches,
            key=lambda match: match.start(),
        )
        reference_text = text[heading_match.end():]

    if not reference_text:
        return []
    
    stop_patterns = [
        r"\bappendix\b",
        r"\backnowledg",
        r"\bauthor biography\b"
    ]

    for stop in stop_patterns:
        stop_match = re.search(stop, reference_text, re.I)

        if stop_match:
            reference_text = reference_text[
                :stop_match.start()
            ]

    reference_text = re.sub(r"\n+", "\n", reference_text)
    reference_text = re.sub(r"\n\s*\d+\s*\n", "\n", reference_text)

    lines = reference_text.split("\n")
    cleaned_lines = [
        clean_text(line)
        for line in lines
        if clean_text(line)
    ]
    line_counts = Counter(line.lower() for line in cleaned_lines)
    numbered_mode = sum(
        1 for line in cleaned_lines
        if re.match(r"^\d{1,3}[.)]\s+", line)
    ) >= 2

    references = []
    current_ref = ""

    for line in lines:
        line = clean_text(line)

        if not line:
            continue
        if re.fullmatch(r"\d{1,4}", line):
            continue

        is_numbered_ref = bool(re.match(r"^\d{1,3}[.)]\s+", line))
        
        if (
            line_counts[line.lower()] > 1
            and not is_numbered_ref
        ):
            continue

        is_new_ref = re.match(
            r""" ^(
                [-*•]\s+|\[\d+\]|\(\d+\)|\d+[\.\)]|
                [A-Z][a-z]+,\s*[A-Z] | [A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2}\s*\(\d{4}\)
            )
            """, line, re.X
        )
        is_new_ref = is_new_ref or _starts_like_reference_entry(line)

        if numbered_mode:
            is_new_ref = is_numbered_ref
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
        references.append(current_ref.strip())
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
                    r"^\s*([-*•]\s+|\[\d+\]|\(\d+\)|"
                    r"\d+[\.\)]|[A-Z][a-z]+,\s*[A-Z])",
                    line
                )
            )
            starts_new = starts_new or _starts_like_reference_entry(line)

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
        ref = re.sub(r"\s+", " ", ref)

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
