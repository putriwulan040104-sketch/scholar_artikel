import re
from urllib.parse import urljoin

import requests

from src.scraper.html_parser import normalize_doi
from src.scraper.source_selector import classify_pdf_source, choose_pdf_url


def fetch_doi_crossref(title, authors=""):
    """Mencari DOI melalui CrossRef ketika DOI tidak tersedia dari metadata Google Scholar."""
    try:
        params = {"query.title": title, "rows": 1, "select": "DOI,title,score"}
        if authors:
            last = authors.split(",")[0].strip().split()[-1]
            params["query.author"] = last

        r = requests.get(
            "https://api.crossref.org/works",
            params=params,
            timeout=8,
            headers={"User-Agent": "ScholarScraper/2.0 (mailto:research@example.com)"},
        )
        if r.status_code == 200:
            items = r.json().get("message", {}).get("items", [])
            if items and items[0].get("score", 0) >= 30:   # threshold relevansi
                doi = normalize_doi(items[0].get("DOI", ""))
                if doi:
                    print(f"  🔎 CrossRef DOI: {doi}")
                    return doi
    except Exception as e:
        print(f"  ⚠ CrossRef: {e}")
    return None


def fetch_doi_from_doi_org(url):
    """Mengecek DOI dari URL artikel atau redirect URL publisher."""
    if not url:
        return None
    try:
        # Kadang URL artikel langsung mengandung DOI
        doi = normalize_doi(url)
        if doi:
            return doi
        # Coba ikuti redirect (tanpa render JS) untuk dapat URL final
        r = requests.head(url, allow_redirects=True, timeout=8,
                headers={"User-Agent": "Mozilla/5.0"})
        final = r.url
        doi = normalize_doi(final)
        if doi:
            print(f"  🌐 DOI dari redirect URL: {doi}")
            return doi
    except Exception:
        pass
    return None


def _clean_candidate_pdf_url(candidate_url, base_url):
    """Menormalkan kandidat URL PDF relatif menjadi URL absolut."""
    if not candidate_url:
        return None
    candidate_url = candidate_url.strip().strip("\"'")
    if not candidate_url or candidate_url.startswith(("javascript:", "mailto:")):
        return None
    return urljoin(base_url, candidate_url)


def _looks_like_pdf_url(candidate_url):
    """Mendeteksi apakah sebuah URL terlihat seperti link PDF/download artikel."""
    if not candidate_url:
        return False
    lower_url = candidate_url.lower()
    return (
        ".pdf" in lower_url
        or "/pdf" in lower_url
        or "download" in lower_url
        or "article/download" in lower_url
    )


def extract_pdf_url_from_publisher_page(html, base_url):
    """Mencari URL PDF resmi dari HTML halaman publisher hasil resolusi DOI."""
    if not html:
        return None

    candidates = []
    meta_patterns = [
        r'<meta[^>]+name=["\']citation_pdf_url["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']citation_pdf_url["\']',
        r'<meta[^>]+property=["\']citation_pdf_url["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']citation_pdf_url["\']',
    ]
    for pattern in meta_patterns:
        candidates.extend(re.findall(pattern, html, flags=re.IGNORECASE))

    href_candidates = re.findall(
        r'<(?:a|link)[^>]+href=["\']([^"\']+)["\'][^>]*',
        html,
        flags=re.IGNORECASE,
    )
    candidates.extend(url for url in href_candidates if _looks_like_pdf_url(url))

    cleaned_candidates = []
    for candidate in candidates:
        pdf_url = _clean_candidate_pdf_url(candidate, base_url)
        if pdf_url and _looks_like_pdf_url(pdf_url):
            cleaned_candidates.append(pdf_url)

    return choose_pdf_url(cleaned_candidates)


def resolve_doi_url(doi):
    """Melakukan resolusi DOI ke halaman publisher resmi."""
    if not doi:
        return None, None, None
    doi_url = f"https://doi.org/{doi}"
    try:
        response = requests.get(
            doi_url,
            allow_redirects=True,
            timeout=12,
            headers={
                "User-Agent": "Mozilla/5.0",
                "Accept": "text/html,application/pdf;q=0.9,*/*;q=0.8",
            },
        )
        final_url = response.url
        content_type = response.headers.get("content-type", "").lower()
        if "application/pdf" in content_type or _looks_like_pdf_url(final_url):
            return final_url, final_url, response
        return final_url, None, response
    except Exception as e:
        print(f"  DOI resolve gagal: {e}")
        return None, None, None


def find_official_pdf_from_doi(doi):
    """Mencari PDF resmi melalui halaman publisher hasil resolusi DOI."""
    official_url, direct_pdf_url, response = resolve_doi_url(doi)
    if direct_pdf_url:
        return official_url, direct_pdf_url
    if not response:
        return official_url, None

    official_pdf_url = extract_pdf_url_from_publisher_page(
        response.text,
        official_url or response.url,
    )
    return official_url, official_pdf_url


def log_doi_pdf_resolution(doi, official_url, official_pdf_url, fallback_pdf_url, selected_pdf_url):
    """Menampilkan keputusan pemilihan PDF resmi atau fallback Google Scholar."""
    fallback_info = classify_pdf_source(fallback_pdf_url)
    selected_info = classify_pdf_source(selected_pdf_url)

    if official_pdf_url:
        decision = "Use Official PDF"
    elif fallback_pdf_url:
        if selected_info["pdf_source_type"] == "Mirror Platform":
            decision = "Use Mirror PDF"
        elif selected_info["pdf_source_type"] == "Institutional Repository":
            decision = "Use Repository PDF"
        else:
            decision = "Use Google Scholar PDF"
    else:
        decision = "No PDF URL"

    print("-" * 50)
    print("DOI :")
    print(doi or "-")
    print()
    print("Resolving DOI...")
    print()
    print("Official URL :")
    print(official_url or "-")
    print()
    print("Official PDF :")
    print("Found" if official_pdf_url else "Not Found")
    print()
    if not official_pdf_url:
        print("Fallback :")
        if fallback_pdf_url:
            print(f"Google Scholar PDF ({fallback_info['pdf_domain'] or '-'})")
        else:
            print("-")
        print()
    print("Decision :")
    print(decision)
    print("-" * 50)


def select_pdf_url_for_article(doi, scholar_pdf_url):
    """Memilih PDF official dari DOI jika ada, atau fallback ke PDF Google Scholar."""
    official_url = None
    official_pdf_url = None

    if doi:
        official_url, official_pdf_url = find_official_pdf_from_doi(doi)
    selected_pdf_url = official_pdf_url or scholar_pdf_url
    if doi:
        log_doi_pdf_resolution(
            doi,
            official_url,
            official_pdf_url,
            scholar_pdf_url,
            selected_pdf_url,
        )
    return selected_pdf_url
