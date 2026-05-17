from app.db import supabase

from app.services.article_service import (
    extract_article
)

from app.services.pdf_service import (
    download_pdf,
    extract_pdf_content,
    remove_pdf
)

from app.models.publication_model import (
    build_publication
)

SOURCE_TABLE = "scholar_articles"

TARGET_TABLE = "publications"


# ==========================================
# GET ARTICLES
# ==========================================

def get_articles():

    response = (
        supabase
        .table(SOURCE_TABLE)
        .select("id, title, authors, year, source, url, pdf_url")
        .execute()
    )

    return response.data


# ==========================================
# SAVE PUBLICATION
# ==========================================

def save_publication(data):

    response = (
        supabase
        .table(TARGET_TABLE)
        .insert(data)
        .execute()
    )

    return response


# ==========================================
# PROCESS ARTICLES
# ==========================================

def process_articles():

    articles = get_articles()

    results = []

    for article in articles:

        try:

            url = article.get("url")

            pdf_url = article.get("pdf_url")

            content = None
            metadata = None

            # ==================================
            # PDF EXTRACTION
            # ==================================

            if pdf_url:

                print(
                    f"Processing PDF: {pdf_url}"
                )

                try:

                    pdf_path = download_pdf(
                        pdf_url
                    )

                    content = extract_pdf_content(
                        pdf_path
                    )

                    remove_pdf(pdf_path)

                except Exception as pdf_error:

                    print(
                        "PDF Error:",
                        pdf_error
                    )

            # ==================================
            # ARTICLE EXTRACTION
            # ==================================

            if not content and url:

                print(
                    f"Processing Article: {url}"
                )

                article_result = extract_article(
                    url
                )

                if article_result:

                    metadata = article_result[
                        "metadata"
                    ]

                    content = article_result[
                        "content"
                    ]

            if not content:
                continue

            publication = build_publication(
                article,
                metadata,
                content
            )

            save_publication(publication)

            results.append({
                "title":
                    publication["title"],

                "status":
                    "saved"
            })

        except Exception as e:

            results.append({

                "article_url":
                    article.get("url"),

                "status":
                    "error",

                "message":
                    str(e)
            })

    return results