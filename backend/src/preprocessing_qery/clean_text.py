# src/preprocessing/clean_text.py
import re
import string
from typing import Optional

def clean_text(text: Optional[str]) -> str:
    if not isinstance(text, str) or not text.strip():
        return ""
    # clean_text.py (inti)
    text = re.sub(r'http\S+|www\.\S+', ' ', text)
    text = text.replace('-', ' ')              
    text = re.sub(r'[^a-zA-Z0-9\s]', ' ', text)  
    text = re.sub(r'\s+', ' ', text).strip()
    return text