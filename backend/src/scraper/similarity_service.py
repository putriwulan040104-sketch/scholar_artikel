import re

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from src.scraper.source_selector import get_source_label, select_best_article_from_group


def preprocess_similarity_text(text):
    """Membersihkan teks sederhana sebelum masuk ke TF-IDF Vector Space Model."""
    text = (text or "").lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def build_similarity_document(article):
    """Menggabungkan title dan abstract sebagai dokumen pembanding metadata."""
    return preprocess_similarity_text(
        f"{article.get('title', '')} {article.get('abstract', '')}"
    )


def calculate_cosine_similarity_matrix(articles):
    """Menghitung TF-IDF dan cosine similarity untuk seluruh artikel sementara."""
    if not articles:
        return []

    documents = [build_similarity_document(article) for article in articles]
    if not any(documents):
        return [[1.0 if i == j else 0.0 for j in articles] for i in articles]

    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform(documents)
    return cosine_similarity(tfidf_matrix)


def group_duplicate_articles(articles, threshold):
    """Mengelompokkan artikel yang similarity title+abstract-nya melewati threshold."""
    if len(articles) <= 1:
        return [[i] for i in range(len(articles))], None

    similarity_matrix = calculate_cosine_similarity_matrix(articles)
    parent = list(range(len(articles)))

    def find(index):
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    def union(left, right):
        root_left = find(left)
        root_right = find(right)
        if root_left != root_right:
            parent[root_right] = root_left

    for i in range(len(articles)):
        for j in range(i + 1, len(articles)):
            if similarity_matrix[i][j] >= threshold:
                union(i, j)

    grouped = {}
    for index in range(len(articles)):
        grouped.setdefault(find(index), []).append(index)

    return list(grouped.values()), similarity_matrix


def get_group_similarity(group_indexes, similarity_matrix):
    """Mengambil nilai similarity tertinggi dalam satu grup duplicate untuk kebutuhan logging."""
    if similarity_matrix is None or len(group_indexes) <= 1:
        return 1.0
    scores = []
    for position, left in enumerate(group_indexes):
        for right in group_indexes[position + 1:]:
            scores.append(float(similarity_matrix[left][right]))
    return max(scores) if scores else 1.0


def log_similarity_group(group_number, group_articles, keep_article, similarity_score):
    """Menampilkan log keputusan keep/remove untuk setiap grup duplicate."""
    print("=" * 50)
    print(f"Similarity Group #{group_number}")
    print()
    print(f"Similarity: {similarity_score:.2f}")
    print()
    print("Candidate :")
    for article in group_articles:
        print(f"- {get_source_label(article)}")
    print()
    print("Decision :")
    for article in group_articles:
        action = "KEEP" if article is keep_article else "REMOVE"
        print(f"{action} {get_source_label(article)}")
    print("=" * 50)


def filter_articles_by_similarity_and_source(articles, threshold, progress_callback=None):
    """Menjalankan TF-IDF cosine similarity, grouping duplicate, lalu memilih sumber terbaik."""
    if not articles:
        return []

    if progress_callback:
        progress_callback({
            "stage": "analyze",
            "event": "start",
            "message": f"Menganalisis kecocokan {len(articles)} artikel...",
            "article_count": len(articles),
        })
    groups, similarity_matrix = group_duplicate_articles(articles, threshold)
    duplicate_groups = sum(1 for group in groups if len(group) > 1)
    duplicate_articles = sum(max(len(group) - 1, 0) for group in groups)
    if progress_callback:
        progress_callback({
            "stage": "analyze",
            "event": "done",
            "message": "Kecocokan artikel selesai dihitung",
            "article_count": len(articles),
        })
        progress_callback({
            "stage": "group",
            "event": "start",
            "message": "Mengelompokkan artikel yang memiliki isi serupa...",
            "article_count": len(articles),
        })
        progress_callback({
            "stage": "group",
            "event": "done",
            "message": (
                f"Artikel duplikat: {duplicate_articles} "
                f"dalam {duplicate_groups} kelompok"
            ),
            "group_count": len(groups),
            "duplicate_group_count": duplicate_groups,
            "duplicate_count": duplicate_articles,
        })

    selected_indexes = []
    duplicate_group_number = 1

    if progress_callback:
        progress_callback({
            "stage": "source",
            "event": "start",
            "message": "Memilih sumber terbaik dari setiap kelompok artikel...",
            "group_count": len(groups),
        })

    for group_indexes in groups:
        if len(group_indexes) == 1:
            selected_indexes.append(group_indexes[0])
            continue

        keep_index = select_best_article_from_group(articles, group_indexes)
        selected_indexes.append(keep_index)
        group_articles = [articles[index] for index in group_indexes]
        log_similarity_group(
            duplicate_group_number,
            group_articles,
            articles[keep_index],
            get_group_similarity(group_indexes, similarity_matrix),
        )
        duplicate_group_number += 1

    selected_indexes.sort()
    selected_articles = [articles[index] for index in selected_indexes]
    if progress_callback:
        progress_callback({
            "stage": "source",
            "event": "done",
            "message": f"Sumber terpercaya terpilih: {len(selected_articles)} artikel",
            "selected_count": len(selected_articles),
        })
    return selected_articles
