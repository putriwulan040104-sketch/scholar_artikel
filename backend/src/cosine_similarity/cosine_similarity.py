# src/tfidf/cosine_similarity.py
import os
import re
import json
import numpy as np
import pandas as pd
import scipy.sparse as sp

from collections import Counter
from sklearn.metrics.pairwise import cosine_similarity


def clean_text(text):
    text = str(text).lower()
    text = re.sub(r"http\S+|www\S+", " ", text)
    text = re.sub(r"[^a-zA-Z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def load_vsm(tfidf_dir: str):
    tfidf_matrix = sp.load_npz(os.path.join(tfidf_dir, "tfidf_matrix.npz"))

    with open(os.path.join(tfidf_dir, "tfidf_terms.json"), "r", encoding="utf-8") as file:
        terms = json.load(file)

    with open(os.path.join(tfidf_dir, "tfidf_doc_ids.json"), "r", encoding="utf-8") as file:
        doc_ids = json.load(file)

    with open(os.path.join(tfidf_dir, "idf_scores.json"), "r", encoding="utf-8") as file:
        idf_scores = json.load(file)

    documents = pd.read_csv(os.path.join(tfidf_dir, "tfidf_documents.csv"))

    return tfidf_matrix, terms, doc_ids, idf_scores, documents


def preprocess_query(query: str, stop_words: set, stemmer):
    cleaned = clean_text(query)
    tokens = cleaned.split()
    tokens = [token for token in tokens if token not in stop_words and len(token) > 1]
    tokens = [stemmer.stem(token) for token in tokens]
    return tokens


def build_query_vector(query_tokens: list, terms: list, idf_scores: dict):
    term_to_index = {term: index for index, term in enumerate(terms)}
    query_vector = np.zeros(len(terms), dtype=float)

    if not query_tokens:
        return query_vector.reshape(1, -1)

    total_terms = len(query_tokens)
    term_counts = Counter(query_tokens)

    for term, count in term_counts.items():
        if term in term_to_index:
            tf = count / total_terms
            idf = float(idf_scores.get(term, 0))
            query_vector[term_to_index[term]] = tf * idf

    return query_vector.reshape(1, -1)


def count_occurrence(document_text: str, query_tokens: list):
    document_tokens = str(document_text).split()
    return sum(document_tokens.count(term) for term in query_tokens)


def interpret_similarity(score: float, threshold: float = 0.3):
    if score > 0.5:
        return "Relevan Tinggi"
    if score > threshold:
        return "Relevan Sedang"
    return "Rendah"


def is_direct_pdf(url: str):
    if pd.isna(url):
        return False

    url = str(url).lower()

    return (
        url.endswith(".pdf")
        or "/pdf/" in url
        or "arxiv.org/pdf" in url
        or "pmc.ncbi.nlm.nih.gov" in url
        or "jmlr.org" in url
    )


def search(
    query: str,
    tfidf_matrix,
    terms: list,
    idf_scores: dict,
    doc_index: pd.DataFrame,
    stop_words: set,
    stemmer,
    top_k: int = 10,
    min_occurrence: int = 0,
    threshold: float = 0.3,
):
    query_tokens = preprocess_query(query, stop_words, stemmer)

    if not query_tokens:
        return pd.DataFrame()

    query_vector = build_query_vector(query_tokens, terms, idf_scores)
    scores = cosine_similarity(query_vector, tfidf_matrix).flatten()

    results = doc_index.copy()
    results["similarity_score"] = scores
    results["occurrence"] = results["document_text"].apply(
        lambda text: count_occurrence(text, query_tokens)
    )

    results = results[results["similarity_score"] > 0].copy()

    if min_occurrence > 0:
        results = results[results["occurrence"] >= min_occurrence].copy()

    results = results.sort_values("similarity_score", ascending=False)
    results = results.head(top_k).reset_index(drop=True)

    results["rank"] = range(1, len(results) + 1)
    results["interpretation"] = results["similarity_score"].apply(
        lambda score: interpret_similarity(score, threshold)
    )

    if "pdf_url" in results.columns:
        results["is_pdf"] = results["pdf_url"].apply(is_direct_pdf)
        results["access_url"] = results.apply(
            lambda row: row["pdf_url"] if row["is_pdf"] else row.get("url", ""),
            axis=1,
        )

    return results