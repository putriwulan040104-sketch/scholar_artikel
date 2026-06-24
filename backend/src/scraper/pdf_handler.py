import io
import os
import re
import requests
from PyPDF2 import PdfReader
from src.config.settings import PDF_DIR

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


def download_pdf(pdf_url, title, driver=None):    
    safe_title = re.sub(r"[^\w]+", "_", title)[:80]
    file_path = os.path.join(PDF_DIR, f"{safe_title}.pdf")
    headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "application/pdf,application/octet-stream,*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://scholar.google.com/",
        }
    response = requests.get(pdf_url,headers=headers,timeout=20,allow_redirects=True,
            stream=True,
        )
    content_type = response.headers.get("Content-Type", "").lower()
        # Baca chunk pertama untuk cek magic bytes
    first_chunk = b""
    all_chunks = []
    for chunk in response.iter_content(8192):
            if chunk:
                if not first_chunk:
                    first_chunk = chunk
                all_chunks.append(chunk)
    is_pdf = "pdf" in content_type or first_chunk[:4] == b"%PDF"
    if response.status_code == 200 and is_pdf:
            with open(file_path, "wb") as f:
                for chunk in all_chunks:f.write(chunk)
            if is_pdf_valid(file_path):
                print("PDF valid")
                return file_path
            else:
                os.remove(file_path)
                print("  ⚠ PDF corrupt, dihapus")       
    return None

def is_pdf_valid(path):
    try:
        reader = PdfReader(path)
        return len(reader.pages) > 0
    except Exception:
        return False


def extract_doi_from_pdf(pdf_path):
    """
    Ekstrak DOI dari file PDF yang sudah diunduh.
    Cek metadata dulu, lalu teks 3 halaman pertama.
    """
    if not pdf_path or not os.path.exists(pdf_path):
        return None

    try:
        reader = PdfReader(pdf_path)

        # 1. Cek metadata PDF
        metadata = reader.metadata or {}
        for key in ["/Subject", "/Keywords", "/Description", "/DOI", "/doi"]:
            val = str(metadata.get(key, "") or "")
            if val:
                doi = normalize_doi(val)
                if doi:
                    print(f"  📎 DOI dari metadata PDF: {doi}")
                    return doi

        # 2. Cek teks halaman (maks 3 halaman pertama)
        max_pages = min(3, len(reader.pages))
        for i in range(max_pages):
            try:
                text = reader.pages[i].extract_text() or ""
                # Cari pola DOI di teks
                match = DOI_PATTERN.search(text)
                if match:
                    doi = normalize_doi(match.group(1))
                    if doi:
                        print(f"  📄 DOI dari halaman {i+1} PDF: {doi}")
                        return doi
            except Exception:
                continue

    except Exception as e:
        print(f"  ⚠ Gagal baca PDF: {e}")

    return None