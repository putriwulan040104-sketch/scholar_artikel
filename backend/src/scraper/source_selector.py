from urllib.parse import urlparse


def identify_pdf_domain(pdf_url):
    """Mengambil domain dari URL PDF untuk klasifikasi sumber."""
    if not pdf_url:
        return None
    try:
        domain = urlparse(pdf_url).netloc.lower()
        if domain.startswith("www."):
            domain = domain[4:]
        return domain or None
    except Exception:
        return None


def classify_pdf_source(pdf_url):
    """Mengelompokkan URL PDF menjadi official publisher, journal, repository, atau mirror."""
    pdf_domain = identify_pdf_domain(pdf_url)
    if not pdf_domain:
        return {
            "pdf_domain": None,
            "pdf_source_type": None,
            "is_official_pdf": False,
        }

    parsed_url = urlparse(pdf_url)
    pdf_path = (parsed_url.path or "").lower()
    official_domains = [
        "ieeexplore.ieee.org",
        "dl.acm.org",
        "link.springer.com",
        "sciencedirect.com",
        "onlinelibrary.wiley.com",
        "nature.com",
        "mdpi.com",
        "tandfonline.com",
        "journals.sagepub.com",
        "emerald.com",
    ]
    official_label_prefixes = ("jurnal", "journal", "ejournal", "ejurnal", "ojs")
    official_journal_article_paths = (
        "/article/view",
        "/article/download",
        "/article/viewfile",
    )
    mirror_domains = [
        "academia.edu",
        "researchgate.net",
        "pdfs.semanticscholar.org",
        "scholar.archive.org",
    ]

    is_mirror = any(
        pdf_domain == domain or pdf_domain.endswith(f".{domain}")
        for domain in mirror_domains
    )
    if is_mirror:
        return {
            "pdf_domain": pdf_domain,
            "pdf_source_type": "Mirror Platform",
            "is_official_pdf": False,
        }

    is_repository = any(
        pattern in pdf_domain
        for pattern in ("repository", "eprints", "digilib", "library")
    )
    if is_repository:
        return {
            "pdf_domain": pdf_domain,
            "pdf_source_type": "Institutional Repository",
            "is_official_pdf": False,
        }

    is_official_publisher = any(
        pdf_domain == domain or pdf_domain.endswith(f".{domain}")
        for domain in official_domains
    )
    if is_official_publisher:
        return {
            "pdf_domain": pdf_domain,
            "pdf_source_type": "Official Publisher",
            "is_official_pdf": True,
        }

    is_official_journal_domain = any(
        label.startswith(official_label_prefixes)
        for label in pdf_domain.split(".")
    )
    has_official_journal_article_path = any(
        pattern in pdf_path
        for pattern in official_journal_article_paths
    )
    is_official_journal_path = (
        "/ojs/" in pdf_path
        or has_official_journal_article_path
        or ("/index.php/" in pdf_path and has_official_journal_article_path)
    )
    if is_official_journal_domain or is_official_journal_path:
        return {
            "pdf_domain": pdf_domain,
            "pdf_source_type": "Official Journal",
            "is_official_pdf": True,
        }

    return {
        "pdf_domain": pdf_domain,
        "pdf_source_type": "Mirror Platform",
        "is_official_pdf": False,
    }


def _pdf_source_priority(pdf_url):
    """Memberi skor prioritas URL PDF berdasarkan klasifikasi sumber."""
    pdf_info = classify_pdf_source(pdf_url)
    priority = {
        "Official Publisher": 4,
        "Official Journal": 3,
        "Institutional Repository": 2,
        "Mirror Platform": 1,
    }
    return priority.get(pdf_info["pdf_source_type"], 0)


def choose_pdf_url(pdf_urls):
    """Memilih URL PDF terbaik dari beberapa kandidat Google Scholar."""
    pdf_urls = [url for url in pdf_urls if url]
    if not pdf_urls:
        return None
    return max(pdf_urls, key=_pdf_source_priority)


def get_source_label(article):
    """Memberikan label sumber yang mudah dibaca untuk logging kandidat duplicate."""
    inferred_pdf_info = classify_pdf_source(article.get("pdf_url"))
    pdf_source_type = article.get("pdf_source_type") or inferred_pdf_info["pdf_source_type"]
    source_text = " ".join(
        str(article.get(key) or "")
        for key in ("source", "publisher", "pdf_domain", "pdf_source_type", "url", "pdf_url")
    ).lower()

    labels = [
        ("ieee", "IEEE"),
        ("acm", "ACM"),
        ("springer", "Springer"),
        ("elsevier", "Elsevier"),
        ("sciencedirect", "Elsevier"),
        ("wiley", "Wiley"),
        ("nature", "Nature"),
        ("taylor & francis", "Taylor & Francis"),
        ("tandfonline", "Taylor & Francis"),
        ("sage", "SAGE"),
        ("emerald", "Emerald"),
        ("mdpi", "MDPI"),
        ("academia.edu", "Academia"),
        ("pdfs.semanticscholar.org", "Semantic Scholar"),
        ("semanticscholar", "Semantic Scholar"),
        ("researchgate", "ResearchGate"),
        ("scribd", "Scribd"),
    ]
    for keyword, label in labels:
        if keyword in source_text:
            return label

    if pdf_source_type == "Official Publisher":
        return "Official Publisher"
    if pdf_source_type == "Official Journal":
        return "Official Journal"
    if pdf_source_type == "Institutional Repository":
        return "Institutional Repository"
    if article.get("pdf_url"):
        return "Google Scholar PDF"
    return "Mirror Platform"


def get_official_source_priority(article):
    """Mengubah urutan prioritas sumber menjadi skor numerik untuk pemilihan artikel terbaik."""
    label = get_source_label(article)
    inferred_pdf_info = classify_pdf_source(article.get("pdf_url"))
    pdf_source_type = article.get("pdf_source_type") or inferred_pdf_info["pdf_source_type"]
    label_priority = {
        "IEEE": 120,
        "ACM": 119,
        "Springer": 118,
        "Elsevier": 117,
        "Wiley": 116,
        "Nature": 115,
        "Taylor & Francis": 114,
        "SAGE": 113,
        "Emerald": 112,
        "MDPI": 111,
        "Official Publisher": 110,
        "Official Journal": 100,
        "Institutional Repository": 80,
        "Google Scholar PDF": 60,
        "Academia": 30,
        "Semantic Scholar": 25,
        "ResearchGate": 20,
        "Scribd": 10,
        "Mirror Platform": 1,
    }
    pdf_type_bonus = {
        "Official Publisher": 5,
        "Official Journal": 4,
        "Institutional Repository": 2,
        "Mirror Platform": 0,
    }
    return (
        label_priority.get(label, 1),
        pdf_type_bonus.get(pdf_source_type, 0),
        1 if article.get("is_official_pdf") or inferred_pdf_info["is_official_pdf"] else 0,
        int(article.get("year") or 0),
    )


def select_best_article_from_group(articles, group_indexes):
    """Memilih satu artikel terbaik dari grup duplicate berdasarkan official source priority."""
    return max(group_indexes, key=lambda index: get_official_source_priority(articles[index]))


def log_pdf_source_validation(publisher, pdf_info):
    """Menampilkan keputusan penyimpanan berdasarkan tipe sumber PDF."""
    decision = "SAVE"
    if pdf_info["pdf_source_type"] in ("Institutional Repository", "Mirror Platform"):
        decision = "SAVE (Mirror)"

    print("-" * 42)
    print("Publisher :")
    print(publisher or "-")
    print()
    print("PDF Domain :")
    print(pdf_info["pdf_domain"] or "-")
    print()
    print("PDF Source :")
    print(pdf_info["pdf_source_type"] or "-")
    print()
    print("Decision :")
    print(decision)
    print("-" * 42)
