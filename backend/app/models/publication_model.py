import re

import app.services.processing.extraction_service as extractor
import app.services.processing.normalization_service as normalizer


def clean_document_text(text):
    if not text:
        return ""

    text = text.replace("\x0c", "\n")
    text = re.sub(r"-\s*\n\s*", "", text)
    text = re.sub(r"\n{2,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(
        r"R\s*E\s*F\s*E\s*R\s*E\s*N\s*C\s*E\s*S",
        "REFERENCES",
        text,
        flags=re.I,
    )
    text = re.sub(
        r"\bK\s+E\s+Y\s+W\s+O\s+R\s+D\s+S\b",
        "KEYWORDS",
        text,
        flags=re.I,
    )
    return text


def build_publication(
    article,
    content,
    declared_keywords=None,
):
    content = clean_document_text(content)
    extracted_keywords = extractor.extract_keywords(content)
    references = extractor.extract_reference(content)

    if declared_keywords and len(declared_keywords) >= len(extracted_keywords):
        keywords = declared_keywords
    else:
        keywords = extracted_keywords

    return {
        "source_id": article.get("id"),
        "keywords": normalizer.normalize_keywords(keywords),
        "reference_list": normalizer.normalize_reference(references),
    }
