import re

def normalize(text: str):
    text = text.lower()
    text = re.sub(r"[^a-z0-9 ]", "", text)
    return text
