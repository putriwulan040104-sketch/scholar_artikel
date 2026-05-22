# src/preprocessing/tokenizing.py

from typing import List

def tokenizing(text: str) -> List[str]:
    """
    Memecah teks menjadi token/kata
    """

    if not isinstance(text, str):
        return []

    return text.split()