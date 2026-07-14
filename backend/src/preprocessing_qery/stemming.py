# src/preprocessing/stemming.py

from typing import List
from Sastrawi.Stemmer.StemmerFactory import StemmerFactory

# Inisialisasi stemmer sekali saja
factory = StemmerFactory()
stemmer = factory.create_stemmer()
def stemming(tokens: List[str]) -> List[str]:
    """
    Melakukan stemming Bahasa Indonesia
    """

    if not isinstance(tokens, list):
        return []

    return [stemmer.stem(word) for word in tokens]