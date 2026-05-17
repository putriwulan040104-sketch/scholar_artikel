import re

from app.utils.cleaner import clean_text


# ==========================================
# DOI
# ==========================================

def extract_doi(text):

    pattern = r"10\.\d{4,9}/[-._;()/:A-Z0-9]+"

    match = re.search(
        pattern,
        text,
        re.I
    )

    if match:
        return match.group(0)

    return None


# ==========================================
# KEYWORDS
# ==========================================

def extract_keywords(text):

    patterns = [
        r"(keywords|keyword)\s*[:\-]?\s*(.*)",
        r"(kata kunci)\s*[:\-]?\s*(.*)"
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.I
        )

        if match:

            keyword_text = match.group(2)

            keywords = re.split(
                r",|;",
                keyword_text
            )

            return [
                clean_text(k)
                for k in keywords
                if clean_text(k)
            ]

    return []


# ==========================================
# REFERENCE EXTRACTION
# ==========================================

def extract_reference(text):

    # ======================================
    # FIND REFERENCE SECTION
    # ======================================

    patterns = [
        r"references",
        r"reference",
        r"bibliography",
        r"works cited",
        r"daftar pustaka",
        r"referensi"
    ]

    reference_text = None

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.I
        )

        if match:

            start = match.start()

            reference_text = text[start:]

            break

    if not reference_text:
        return []

    # ======================================
    # CLEAN LINES
    # ======================================

    lines = reference_text.split("\n")

    cleaned_lines = []

    for line in lines:

        line = clean_text(line)

        if not line:
            continue

        if len(line) < 15:
            continue

        cleaned_lines.append(line)

    # ======================================
    # MERGE MULTILINE REFERENCES
    # ======================================

    references = []

    current_ref = ""

    citation_patterns = [
        r"^\[\d+\]",
        r"^\d+\.",
        r"^[A-Z][a-zA-Z]+.*, \(\d{4}\)",
        r"^[A-Z][a-zA-Z]+.*\d{4}"
    ]

    for line in cleaned_lines:

        is_new_reference = False

        for pattern in citation_patterns:

            if re.search(pattern, line):

                is_new_reference = True
                break

        if is_new_reference:

            if current_ref:
                references.append(current_ref)

            current_ref = line

        else:

            current_ref += " " + line

    if current_ref:
        references.append(current_ref)

    # ======================================
    # REMOVE DUPLICATE
    # ======================================

    unique_refs = []

    seen = set()

    for ref in references:

        ref = clean_text(ref)

        if ref and ref not in seen:

            unique_refs.append(ref)

            seen.add(ref)

    return unique_refs


# ==========================================
# YEAR
# ==========================================

def extract_year(text):

    years = re.findall(
        r"(19|20)\d{2}",
        text
    )

    if years:

        try:
            return int(years[0])
        except:
            return None

    return None