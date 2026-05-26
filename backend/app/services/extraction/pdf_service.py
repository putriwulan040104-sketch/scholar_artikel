import os
import requests
from pdfminer.high_level import extract_text

# DOWNLOAD PDF
def download_pdf(
    url,
    filename="temp_article.pdf"
):

    response = requests.get(
        url,
        timeout=50
    )

    response.raise_for_status()

    with open(filename, "wb") as f:
        f.write(response.content)

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
    if os.path.exists(path):
        os.remove(path)
