import os
import tempfile
import time

import requests
from pdfminer.high_level import extract_text

PDF_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    ),
    "Accept": "application/pdf,application/octet-stream;q=0.9,*/*;q=0.8",
}

# DOWNLOAD PDF
def download_pdf(
    url,
    filename=None,
    timeout=30,
    max_duration=None,
):
    start_time = time.monotonic()
    if max_duration is None and isinstance(timeout, (int, float)):
        max_duration = timeout

    response = requests.get(
        url,
        headers=PDF_HEADERS,
        timeout=timeout,
        allow_redirects=True,
        stream=True,
    )

    response.raise_for_status()

    if filename is None:
        file_descriptor, filename = tempfile.mkstemp(
            prefix="papercitation_",
            suffix=".pdf",
        )
        os.close(file_descriptor)

    try:
        header_buffer = b""
        header_checked = False
        with open(filename, "wb") as file:
            for chunk in response.iter_content(chunk_size=32768):
                if max_duration and time.monotonic() - start_time > max_duration:
                    raise TimeoutError(
                        "Download PDF melewati batas waktu total"
                    )
                if not chunk:
                    continue

                if not header_checked:
                    header_buffer += chunk
                    if len(header_buffer) < 4:
                        continue
                    if header_buffer[:4] != b"%PDF":
                        raise ValueError("URL tidak mengembalikan berkas PDF")
                    file.write(header_buffer)
                    header_checked = True
                    continue

                file.write(chunk)

        if not header_checked:
            raise ValueError("URL tidak mengembalikan berkas PDF")
    except Exception:
        remove_pdf(filename)
        raise

    return filename

# EXTRACT TEXT PDF
def extract_pdf_content(pdf_path):
    try:
        text = extract_text(pdf_path)

        return text

    except Exception as e:
        print("PDF Extraction Error:", e)

        return None

# DELETE TEMP PDF
def remove_pdf(path):
    if not path:
        return

    for attempt in range(5):
        try:
            if os.path.exists(path):
                os.remove(path)
            return
        except PermissionError:
            if attempt == 4:
                print(
                    f"PDF Cleanup Warning: file masih digunakan: {path}",
                    flush=True,
                )
                return
            time.sleep(0.2 * (attempt + 1))
