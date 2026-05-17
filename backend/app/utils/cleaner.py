import re

def clean_text(text):
  if not text:
    return None
  
  text = re.sub(r"\s+", " ", text)

  return text.strip()

def lowercase_text(text):

  if not text:
    return None

  return text.lower().strip()