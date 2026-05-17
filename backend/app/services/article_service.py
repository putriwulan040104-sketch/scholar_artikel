import trafilatura


def extract_article(url):

    try:

        downloaded = trafilatura.fetch_url(url)

        if not downloaded:
            return None

        metadata = trafilatura.extract_metadata(
            downloaded
        )

        content = trafilatura.extract(
            downloaded,
            include_comments=False,
            include_tables=False
        )

        return {
            "metadata": metadata,
            "content": content
        }

    except Exception as e:

        print("Article Extraction Error:", e)

        return None