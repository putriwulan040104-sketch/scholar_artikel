import os
import re
import requests
from PyPDF2 import PdfReader
from src.config.settings import PDF_DIR


def download_pdf(pdf_url, title, driver=None):
    safe_title = re.sub(r"[^\w]+", "_", title)[:80]
    file_path = os.path.join(PDF_DIR, f"{safe_title}.pdf")

    try:
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/pdf,application/octet-stream,*/*"
        }

        print("🔗 Downloading:", pdf_url)

        response = requests.get(
            pdf_url,
            headers=headers,
            timeout=30,
            allow_redirects=True,
            stream=True
        )

        content_type = response.headers.get("Content-Type", "").lower()
        print("📄 Content-Type:", content_type)

        # ✅ cek apakah benar PDF
        if response.status_code == 200 and (
            "pdf" in content_type or response.raw.read(4) == b"%PDF"
        ):
            response.raw.decode_content = True

            with open(file_path, "wb") as f:
                for chunk in response.iter_content(1024):
                    if chunk:
                        f.write(chunk)

            if is_pdf_valid(file_path):
                print("✅ PDF valid")
                return file_path
            else:
                os.remove(file_path)
                print("⚠ PDF corrupt dihapus")

        else:
            print("❌ Bukan PDF langsung, coba fallback Selenium...")

            # 🔥 fallback pakai selenium kalau ada driver
            if driver:
                driver.get(pdf_url)

                # tunggu redirect
                import time
                time.sleep(5)

                final_url = driver.current_url
                print("🔁 Redirect ke:", final_url)

                if ".pdf" in final_url:
                    return download_pdf(final_url, title)

    except Exception as e:
        print(f"⚠ Error download PDF: {e}")

    return None


def is_pdf_valid(path):
    try:
        PdfReader(path)
        return True
    except Exception:
        return False