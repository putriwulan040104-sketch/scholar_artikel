import re

def clean_text(text):
  if not text:
    return ""
  
  text = str(text)
  text = re.sub(r"\s+", " ", text)

  return text.strip()

def lowercase_text(text):

  if not text:
    return ""

  return str(text).lower().strip()