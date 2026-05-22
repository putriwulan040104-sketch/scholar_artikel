# src/preprocessing/casefolding.py

from typing import Optional

def casefolding(text: Optional[str]) -> str:
    """
    Mengubah seluruh teks menjadi huruf kecil
    """

    if not isinstance(text, str):
        return ""

    return text.lower()