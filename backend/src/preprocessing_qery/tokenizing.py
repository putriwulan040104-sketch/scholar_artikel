# src/preprocessing/tokenizing.py

import re
from typing import List

def tokenizing(text: str) -> List[str]:
        if not isinstance(text, str):
            return []
        # tokenizing.py (inti)
        return re.findall(r'[a-z0-9]+', text.lower())

    