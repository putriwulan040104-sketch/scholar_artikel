import io
import requests
import pdfplumber
import re


def extract_references_from_pdf(url: str):

    try:
        print("Downloading:", url)

        r = requests.get(url, timeout=20)

        with pdfplumber.open(io.BytesIO(r.content)) as pdf:
            text = ""
            for page in pdf.pages:
                text += page.extract_text() or ""

        parts = re.split(
            r"references|bibliography|daftar pustaka|works cited",
            text,
            flags=re.I
        )

        if len(parts) < 2:
            print("No reference section found")
            return []

        lines = parts[1].split("\n")

        refs = [l.strip().lower() for l in lines if len(l) > 30]

        print("refs found:", len(refs))

        return refs

    except Exception as e:
        print("PDF parse error:", e)
        return []
