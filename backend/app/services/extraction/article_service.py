import json
import re
from html.parser import HTMLParser
import requests
import trafilatura


ARTICLE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.9,id;q=0.8",
}
KEYWORD_META_NAMES = {
    "citation_keywords",
    "prism.keyword",
    "citation_keyword",
    "article:tag",
}
TEXT_BLOCK_TAGS = {
    "a", "article", "aside", "br", "button", "dd", "div", "dt", "figcaption",
    "footer", "h1", "h2", "h3", "h4", "h5", "h6", "header", "li", "main", "nav",
    "ol", "p", "section", "span", "td", "th", "tr", "ul",
}
KEYWORD_HEADING_PATTERN = re.compile(
    r"^(keywords?|index\s+terms?|kata\s+kunci|"
    r"additional\s+key\s+words\s+and\s+phrases)$",
    re.I,
)
VISIBLE_KEYWORD_STOP_PATTERN = re.compile(
    r"^(?:"
    r"abstract|article information|article info|author information|"
    r"figures?|references?|related|publication history|history|"
    r"sections?|pdf|cite|tools|share|metrics?|supplementary|"
    r"ccs concepts|acm reference format|"
    r"funding information|acknowledg(?:e)?ments?|"
    r"jel classification|"
    r"profiles?|access this article|log in\b|subscribe\b|"
    r"access to document|fingerprint|keyphrases|view full fingerprint|"
    r"published in\b|issn\b|eissn\b|publisher\b|country of publisher|"
    r"lcc subjects|website\b|about the journal|wechat qr code|"
    r"close\b|back to top|search\b|journals\b|articles\b|data\b|api\b|"
    r"journal csv|oai-pmh|widgets\b|public data dump|openurl|xml\b|"
    r"metadata help|preservation\b|about\b|"
    r"volume\b|issue\b|pages?\b|doi\b"
    r")",
    re.I,
)


class _ArticleMetadataParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.keywords = []
        self.json_ld_blocks = []
        self._inside_json_ld = False
        self._json_ld_parts = []

    def handle_starttag(self, tag, attrs):
        attributes = {
            str(name).lower(): value
            for name, value in attrs
            if name
        }

        if tag.lower() == "meta":
            name = (
                attributes.get("name")
                or attributes.get("property")
                or ""
            ).lower()
            content = (attributes.get("content") or "").strip()
            if name in KEYWORD_META_NAMES and content:
                self.keywords.append(content)

        if (
            tag.lower() == "script"
            and "ld+json" in (
                attributes.get("type") or ""
            ).lower()
        ):
            self._inside_json_ld = True
            self._json_ld_parts = []

    def handle_data(self, data):
        if self._inside_json_ld:
            self._json_ld_parts.append(data)

    def handle_endtag(self, tag):
        if tag.lower() == "script" and self._inside_json_ld:
            self.json_ld_blocks.append(
                "".join(self._json_ld_parts)
            )
            self._inside_json_ld = False
            self._json_ld_parts = []


class _VisibleTextParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.chunks = []
        self._current = []
        self._ignored_depth = 0

    def _flush(self):
        text = re.sub(
            r"\s+",
            " ",
            " ".join(self._current),
        ).strip()
        if text:
            self.chunks.append(text)
        self._current = []

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag in {"script", "style", "noscript"}:
            self._ignored_depth += 1
            return
        if tag in TEXT_BLOCK_TAGS:
            self._flush()

    def handle_data(self, data):
        if self._ignored_depth:
            return
        text = data.strip()
        if text:
            self._current.append(text)

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in {"script", "style", "noscript"}:
            self._ignored_depth = max(0, self._ignored_depth - 1)
            return
        if tag in TEXT_BLOCK_TAGS:
            self._flush()

    def close(self):
        super().close()
        self._flush()


def _split_keywords(value):
    if isinstance(value, list):
        values = value
    else:
        values = re.split(r"[;,|]+", str(value or ""))

    return [
        str(item).strip()
        for item in values
        if str(item).strip()
    ]


def _is_article_schema(value):
    schema_types = value if isinstance(value, list) else [value]
    return any(
        str(schema_type).lower() in {
            "article",
            "newsarticle",
            "report",
            "scholarlyarticle",
            "techarticle",
        }
        for schema_type in schema_types
    )


def _extract_json_ld_keywords(value):
    keywords = []

    if isinstance(value, list):
        for item in value:
            keywords.extend(_extract_json_ld_keywords(item))
        return keywords

    if not isinstance(value, dict):
        return keywords

    graph = value.get("@graph")
    if graph:
        keywords.extend(_extract_json_ld_keywords(graph))

    if _is_article_schema(value.get("@type")):
        keywords.extend(_split_keywords(value.get("keywords")))

    return keywords


def _clean_visible_keyword(value):
    keyword = re.sub(r"\s+", " ", str(value or "")).strip()
    keyword = keyword.strip(" -–—.,;:")
    lower_keyword = keyword.lower()

    if not keyword:
        return None
    if len(keyword) > 80:
        return None
    if KEYWORD_HEADING_PATTERN.match(keyword):
        return None
    if VISIBLE_KEYWORD_STOP_PATTERN.match(keyword):
        return None
    if re.match(r"^[A-Z]\d{2}$", keyword):
        return None
    if re.match(r"^\d{2}\s+[a-z ]+sciences$", keyword, re.I):
        return None
    if re.match(r"^(?:journal article|article|research output)$", keyword, re.I):
        return None
    if re.match(r"^(?:open access|review article|research article)$", keyword, re.I):
        return None
    if re.match(r"^pmid\s*:\s*\d+$", keyword, re.I):
        return None
    if lower_keyword in {
        "pubmed",
        "pubmed abstract",
        "nih",
        "nlm",
        "ncbi",
        "medline",
        "national institutes of health",
        "national center for biotechnology information",
        "national library of medicine",
        "research support",
        "non-u.s. gov't",
        "non-us gov't",
    }:
        return None

    return keyword


def _extract_visible_keyword_section(html):
    parser = _VisibleTextParser()
    try:
        parser.feed(html)
        parser.close()
    except Exception:
        pass

    keywords = []
    chunks = parser.chunks
    KEYWORD_INLINE_PATTERN = re.compile(
        r"^(?:keywords?|index\s+terms?|kata\s+kunci|"
        r"additional\s+key\s+words\s+and\s+phrases)"
        r"\s*[:\-–—]\s*(.+)$",
        re.I,
    )

    for index, chunk in enumerate(chunks):
        inline_match = KEYWORD_INLINE_PATTERN.match(chunk.strip())
        if inline_match:
            inline_text = inline_match.group(1)
            parts = _split_keywords(inline_text)
            for item in parts:
                keyword = _clean_visible_keyword(item)
                if keyword:
                    keywords.append(keyword)
            if keywords:
                break

        heading = chunk.strip(" :")
        if not KEYWORD_HEADING_PATTERN.match(heading):
            continue

        section_keywords = []
        for candidate in chunks[index + 1:index + 40]:
            candidate = candidate.strip()
            if not candidate:
                continue
            stop_candidate = candidate.strip(" -–—.,;:")
            if VISIBLE_KEYWORD_STOP_PATTERN.match(stop_candidate):
                break

            parts = _split_keywords(stop_candidate)
            if len(parts) > 1:
                candidates = parts
            else:
                candidates = [candidate]

            for item in candidates:
                keyword = _clean_visible_keyword(item)
                if keyword:
                    section_keywords.append(keyword)

        if section_keywords:
            keywords.extend(section_keywords)
            break

    return keywords


def _extract_declared_keywords(html):
    if not html:
        return []

    parser = _ArticleMetadataParser()
    try:
        parser.feed(html)
    except Exception:
        pass

    keywords = []
    keywords.extend(parser.keywords)
    keywords.extend(_extract_visible_keyword_section(html))

    for raw_json in parser.json_ld_blocks:
        try:
            value = json.loads(raw_json)
        except (TypeError, ValueError):
            continue
        keywords.extend(_extract_json_ld_keywords(value))

    normalized = []
    seen = set()
    for keyword_group in keywords:
        for keyword in _split_keywords(keyword_group):
            keyword = _clean_visible_keyword(keyword)
            if not keyword:
                continue
            key = keyword.lower()
            if key in seen:
                continue
            seen.add(key)
            normalized.append(keyword)

    return normalized


def _extract_visible_text(html):
    parser = _VisibleTextParser()
    try:
        parser.feed(html)
        parser.close()
    except Exception:
        pass

    return "\n".join(parser.chunks)


def extract_article_from_html(html):
    if not html:
        return None

    content = trafilatura.extract(
        html,
        include_comments=False,
        include_tables=False,
    )
    visible_text = _extract_visible_text(html)

    if visible_text and (
        not content
        or "references" in visible_text.lower()
        and "references" not in (content or "").lower()
    ):
        content = "\n".join(
            part
            for part in [content, visible_text]
            if part
        )

    return {
        "content": content,
        "keywords": _extract_declared_keywords(html),
    }


def _download_article(url, timeout=30):
    downloaded = trafilatura.fetch_url(url)
    if downloaded:
        return downloaded

    response = requests.get(
        url,
        headers=ARTICLE_HEADERS,
        timeout=timeout,
        allow_redirects=True,
    )
    response.raise_for_status()
    return response.text


def extract_article(url, timeout=30):
    try:
        downloaded = _download_article(url, timeout=timeout)
        if not downloaded:
            return None

        return extract_article_from_html(downloaded)

    except Exception as error:
        print("Article Extraction Error:", error)
        return None
