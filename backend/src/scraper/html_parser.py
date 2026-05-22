import re


def extract_references_from_html(driver):
    """
    Extract kemungkinan references dari HTML page
    """
    references = []

    try:
        page_source = driver.page_source
        lines = page_source.split("\n")

        for line in lines:
            line = line.strip()

            if not line:
                continue

            # FILTER biar lebih mendekati referensi ilmiah
            if (
                re.search(r"\b\d{4}\b", line)
                and (
                    "," in line
                    or "http" in line.lower()
                    or re.search(r"\(.+?,\s*\d{4}\)", line)
                )
            ):
                references.append(line)

    except Exception as e:
        print(f"⚠ Error parsing HTML: {e}")
        return ""

    return "\n".join(references)