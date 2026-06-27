import re

DOI_PATTERN = re.compile(
    r"(?:https?://(?:dx\.)?doi\.org/)?(10\.\d{4,9}/[-._;()/:A-Z0-9]+)",
    re.IGNORECASE,
)


def normalize_doi(doi):
    if not doi:
        return None
    match = DOI_PATTERN.search(doi.strip())
    if not match:
        return None
    return match.group(1).rstrip(".,;)").lower()


def doi_to_url(doi):
    doi = normalize_doi(doi)
    return f"https://doi.org/{doi}" if doi else None


def extract_doi_from_html(driver):
    """Ekstrak DOI dari page source HTML."""
    try:
        page_source = driver.page_source
        match = DOI_PATTERN.search(page_source)
        if match:
            return normalize_doi(match.group(1))
    except Exception as e:
        print(f"Error parsing DOI dari HTML: {e}")
    return None


def extract_doi_from_scholar_result(result):
    """
    Ekstrak DOI dari elemen hasil Google Scholar.
    Mencari di: href link judul → teks .gs_a → seluruh teks elemen.
    TIDAK membuka tab/halaman baru — hanya baca data yang sudah ada di DOM.
    """
    # 1. Cari di href link judul artikel
    try:
        title_el = result.find_element("css selector", ".gs_rt")
        links = title_el.find_elements("tag name", "a")
        for link in links:
            href = link.get_attribute("href") or ""
            doi = normalize_doi(href)
            if doi:
                return doi
    except Exception:
        pass

    # 2. Cari di teks .gs_a (metadata: penulis - jurnal, tahun)
    try:
        gs_a_text = result.find_element("css selector", ".gs_a").text
        match = DOI_PATTERN.search(gs_a_text)
        if match:
            doi = normalize_doi(match.group(1))
            if doi:
                return doi
    except Exception:
        pass

    # 3. Cari di seluruh teks elemen result
    try:
        full_text = result.text
        match = DOI_PATTERN.search(full_text)
        if match:
            doi = normalize_doi(match.group(1))
            if doi:
                return doi
    except Exception:
        pass

    # 4. Cari di semua atribut href dalam elemen
    try:
        all_links = result.find_elements("tag name", "a")
        for link in all_links:
            href = link.get_attribute("href") or ""
            doi = normalize_doi(href)
            if doi:
                return doi
    except Exception:
        pass

    return None


def extract_references_from_html(driver):
    references = []
    try:
        page_source = driver.page_source
        lines = page_source.split("\n")
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if (
                re.search(r"\b\d{4}\b", line)
                and (
                    "," in line
                    or "http" in line.lower()
                    or re.search(r"\(.+?,\s*\d{4}\)", line)
                )
            ):
                references.append(line)
    except Exception as e:
        print(f"Error parsing HTML: {e}")
        return ""
    return "\n".join(references)
