# src/preprocessing/clean_text.py
import re
import string
from typing import Optional

def clean_text(text: Optional[str]) -> str:
    """
    Text Cleansing sesuai proposal skripsi
    """
    if not isinstance(text, str) or not text.strip():
        return ""
    
    # Lowercase
    text = text.lower()
    
    # Hapus URL
    text = re.sub(r'http\S+|www\.\S+', '', text)
    
    # Hapus angka
    text = re.sub(r'\d+', '', text)
    
    # Hapus tanda baca dan simbol
    text = text.translate(str.maketrans('', '', string.punctuation))
    
    # Hapus whitespace berlebih
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text