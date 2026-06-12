import os
import sys
import ast
import glob
import json
import numpy as np
import pandas as pd
import scipy.sparse as sp
from collections import Counter
from sklearn.metrics.pairwise import cosine_similarity

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT_DIR = os.path.dirname(BASE_DIR)
sys.path.insert(0, ROOT_DIR)
sys.path.insert(0, BASE_DIR)

from app.db import supabase
from src.preprocessing.clean_text import clean_text
from src.preprocessing.tokenizing import tokenizing
from src.preprocessing.stopwords_id import get_stopwords
from src.preprocessing.stemming import stemming

TFIDF_DIR = os.path.join(BASE_DIR, "data", "tfidf")
COSINE_DIR = os.path.join(BASE_DIR, "data", "cosine_results")


def _format_authors(value):
    if value is None:
        return ""

    if isinstance(value, list):
        cleaned = [str(x).strip() for x in value if str(x).strip()]
        return ", ".join(cleaned)

    s = str(value).strip()
    if not s:
        return ""

    if s.startswith("[") and s.endswith("]"):
        try:
            arr = ast.literal_eval(s)
            if isinstance(arr, list):
                cleaned = [str(x).strip() for x in arr if str(x).strip()]
                return ", ".join(cleaned)
        except Exception:
            pass

    return s


def _format_keywords(value):
    if value is None:
        return []

    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]

    s = str(value).strip()
    if not s:
        return []

    if s.startswith("[") and s.endswith("]"):
        try:
            arr = ast.literal_eval(s)
            if isinstance(arr, list):
                return [str(x).strip() for x in arr if str(x).strip()]
        except Exception:
            pass

    if ";" in s:
        return [x.strip() for x in s.split(";") if x.strip()]
    if "," in s:
        return [x.strip() for x in s.split(",") if x.strip()]

    return [s]


def _clean_cell(val):
    if pd.isna(val):
        return None
    val = str(val).strip()
    if val.lower() in ["", "nan", "none", "null"]:
        return None
    return val


def _is_direct_pdf(url):
    if not isinstance(url, str):
        return False

    u = url.lower()

    return (
        u.endswith(".pdf")
        or ".pdf" in u
        or "/pdf/" in u
        or "arxiv.org/pdf" in u
        or "pmc.ncbi.nlm.nih.gov" in u
        or "jmlr.org" in u
    )


def _fetch_all_supabase(table_name, selected_columns, batch_size=1000):
    rows = []
    offset = 0

    while True:
        res = (
            supabase.table(table_name)
            .select(selected_columns)
            .range(offset, offset + batch_size - 1)
            .execute()
        )

        batch = res.data or []

        if not batch:
            break

        rows.extend(batch)

        if len(batch) < batch_size:
            break

        offset += batch_size

    return rows


def _load_vsm_files():
    tfidf_matrix = sp.load_npz(os.path.join(TFIDF_DIR, "tfidf_matrix.npz"))

    with open(os.path.join(TFIDF_DIR, "tfidf_terms.json"), "r", encoding="utf-8") as file:
        terms = json.load(file)

    with open(os.path.join(TFIDF_DIR, "tfidf_doc_ids.json"), "r", encoding="utf-8") as file:
        doc_ids = json.load(file)

    with open(os.path.join(TFIDF_DIR, "idf_scores.json"), "r", encoding="utf-8") as file:
        idf_scores = json.load(file)

    tfidf_documents = pd.read_csv(os.path.join(TFIDF_DIR, "tfidf_documents.csv"))

    doc_ids = [int(doc_id) for doc_id in doc_ids]

    return tfidf_matrix, terms, doc_ids, idf_scores, tfidf_documents


def _load_doc_index_from_supabase(doc_ids, tfidf_documents):
    selected_columns = (
        "id,title,authors,year,source,category,abstract,"
        "pdf_url,url,scrape_status,cleaned_text"
    )

    rows = _fetch_all_supabase("cleaned_papers_results", selected_columns)

    if not rows:
        raise RuntimeError("Tabel cleaned_papers_results kosong atau gagal diakses.")

    metadata_df = pd.DataFrame(rows)
    metadata_df["id"] = metadata_df["id"].astype("int64")

    required_cols = [
        "id", "title", "authors", "year", "source", "category",
        "abstract", "keywords", "pdf_url", "url", "scrape_status",
        "cleaned_text"
    ]

    for col in required_cols:
        if col not in metadata_df.columns:
            metadata_df[col] = None

    metadata_df["authors"] = metadata_df["authors"].apply(_format_authors)

    doc_index = pd.DataFrame({"id": doc_ids})
    doc_index = doc_index.merge(metadata_df, on="id", how="left")

    if "document_text" in tfidf_documents.columns:
        doc_index = doc_index.merge(
            tfidf_documents[["id", "document_text"]],
            on="id",
            how="left"
        )
    else:
        doc_index["document_text"] = ""

    for col in [
        "title", "authors", "source", "category", "abstract",
        "keywords", "pdf_url", "url", "scrape_status",
        "cleaned_text", "document_text"
    ]:
        if col in doc_index.columns:
            doc_index[col] = doc_index[col].fillna("")

    return doc_index


def _load_cosine_results():
    cosine_files = glob.glob(os.path.join(COSINE_DIR, "similarity_score_*.csv"))

    if not cosine_files:
        return pd.DataFrame()

    cosine_dfs = []

    for file_path in cosine_files:
        df = pd.read_csv(file_path)
        query_name = (
            os.path.basename(file_path)
            .replace("similarity_score_", "")
            .replace(".csv", "")
            .replace("_", " ")
        )
        df["query"] = query_name
        cosine_dfs.append(df)

    return pd.concat(cosine_dfs, ignore_index=True)


tfidf_matrix, terms, doc_ids, idf_scores, tfidf_documents = _load_vsm_files()
doc_index = _load_doc_index_from_supabase(doc_ids, tfidf_documents)
cosine_results = _load_cosine_results()
stop_words = get_stopwords()
term_to_index = {term: index for index, term in enumerate(terms)}

if len(doc_index) != tfidf_matrix.shape[0]:
    raise RuntimeError(
        f"Jumlah data doc_index ({len(doc_index)}) != baris tfidf_matrix ({tfidf_matrix.shape[0]}). "
        "Jalankan ulang TF-IDF dari dataset yang sama."
    )

print(f"VSM loaded: {len(doc_index)} dokumen, vocab {tfidf_matrix.shape[1]} term")


def preprocess_query(query: str):
    text = clean_text(query)
    tokens = tokenizing(text)
    tokens = [token for token in tokens if token not in stop_words and len(token) > 1]
    tokens = stemming(tokens)
    return tokens


def build_query_vector(query_tokens):
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


def count_occurrence(document_text, query_terms):
    document_tokens = str(document_text).split()
    return sum(document_tokens.count(term) for term in query_terms)


def search_articles(
    query,
    top_k=10,
    year_start=None,
    year_end=None,
    jenis_artikel=None,
    jenis_analisis=None,
    jumlah_publikasi=None,
    jumlah_kemunculan=None,
    kategori=None,
):
    query_terms = preprocess_query(query)

    if not query_terms:
        return {
            "articles": [],
            "total_occurrences": 0,
            "paper_count": 0,
            "total_matched": 0,
            "displayed_count": 0,
            "displayed_occurrences": 0,
        }

    query_vec = build_query_vector(query_terms)
    scores = cosine_similarity(query_vec, tfidf_matrix).flatten()
    ranked_idx = np.argsort(scores)[::-1]

    results = doc_index.iloc[ranked_idx][[
        "id", "title", "authors", "year", "source", "category",
        "abstract", "pdf_url", "url", "scrape_status", "document_text"
    ]].copy()

    results["similarity_score"] = scores[ranked_idx]
    results = results[results["similarity_score"] > 0].reset_index(drop=True)

    if year_start is not None and str(year_start).strip() != "":
        results["year"] = pd.to_numeric(results["year"], errors="coerce")
        results = results[results["year"] >= int(year_start)]

    if year_end is not None and str(year_end).strip() != "":
        results["year"] = pd.to_numeric(results["year"], errors="coerce")
        results = results[results["year"] <= int(year_end)]

    if kategori is not None and str(kategori).strip() != "":
        selected_category = str(kategori).strip().lower()
        category_values = results["category"].astype(str).str.strip().str.lower()
        results = results[category_values == selected_category]

    results["pdf_url"] = results["pdf_url"].apply(_clean_cell)
    results["url"] = results["url"].apply(_clean_cell)

    results["access_url"] = results.apply(
        lambda row: row["pdf_url"] if row["pdf_url"] else row["url"],
        axis=1
    )

    results["is_pdf"] = results["access_url"].apply(_is_direct_pdf)

    if jenis_artikel == "open":
        results = results[results["is_pdf"] == True]
    elif jenis_artikel == "close":
        results = results[results["is_pdf"] == False]

    results["term_frequency"] = results["document_text"].apply(
        lambda text: count_occurrence(text, query_terms)
    )

    if jumlah_kemunculan is not None and str(jumlah_kemunculan).strip() != "":
        min_occ = int(jumlah_kemunculan)
        results = results[results["term_frequency"] >= min_occ]

    if jumlah_publikasi is not None and str(jumlah_publikasi).strip() != "":
        top_k = int(jumlah_publikasi)

    total_matched = int(len(results))
    total_occurrences = int(results["term_frequency"].sum())

    results = results.head(int(top_k))
    displayed_count = int(len(results))
    displayed_occurrences = int(results["term_frequency"].sum())

    results["occurrence"] = results["term_frequency"]
    results["jenis_analisis"] = jenis_analisis or ""
    results["rank"] = range(1, len(results) + 1)

    results = results.drop(columns=["document_text"], errors="ignore")
    results = results.fillna("")

    return {
        "articles": results.to_dict("records"),
        "total_occurrences": total_occurrences,
        "paper_count": displayed_count,
        "total_matched": total_matched,
        "displayed_count": displayed_count,
        "displayed_occurrences": displayed_occurrences,
    }


def get_stats():
    kemunculan = {}

    if not cosine_results.empty and "title" in cosine_results.columns:
        kemunculan = cosine_results["title"].value_counts().head(10).to_dict()

    per_tahun = {}

    if "year" in doc_index.columns:
        year_values = pd.to_numeric(doc_index["year"], errors="coerce").dropna()
        per_tahun = {
            int(k): int(v)
            for k, v in year_values.value_counts().sort_index().items()
        }

    per_kategori = {}

    if "category" in doc_index.columns:
        per_kategori = {
            str(k): int(v)
            for k, v in doc_index["category"].value_counts().items()
            if pd.notna(k) and str(k).strip()
        }

    total_sumber = int(doc_index["source"].nunique()) if "source" in doc_index.columns else 0

    return {
        "total_artikel": int(len(doc_index)),
        "total_sumber": total_sumber,
        "per_tahun": per_tahun,
        "per_kategori": per_kategori,
        "top_kemunculan": kemunculan,
    }


def get_category_options():
    if "category" not in doc_index.columns:
        return []

    category_values = doc_index["category"].dropna().astype(str).str.strip()
    category_values = category_values[category_values != ""]
    counts = category_values.value_counts().sort_index()

    return [
        {
            "value": str(category),
            "label": str(category),
            "count": int(count),
        }
        for category, count in counts.items()
    ]


def get_article_by_id(article_id: int):
    row = doc_index[doc_index["id"] == article_id]

    if row.empty:
        return None

    r = row.iloc[0]

    pdf_url = _clean_cell(r.get("pdf_url"))
    url = _clean_cell(r.get("url"))
    access_url = pdf_url if pdf_url else url

    publication_data = None

    try:
        pub_res = (
            supabase.table("publications")
            .select("keywords,journal,doi,article_url,pdf_url")
            .eq("article_id", article_id)
            .limit(1)
            .execute()
        )

        if pub_res.data:
            publication_data = pub_res.data[0]
    except Exception:
        publication_data = None

    pub_keywords = _format_keywords(
        publication_data.get("keywords") if publication_data else None
    )
    pub_journal = _clean_cell(
        publication_data.get("journal") if publication_data else None
    )
    pub_doi = _clean_cell(
        publication_data.get("doi") if publication_data else None
    )
    pub_article_url = _clean_cell(
        publication_data.get("article_url") if publication_data else None
    )
    pub_pdf_url = _clean_cell(
        publication_data.get("pdf_url") if publication_data else None
    )

    final_pdf_url = pub_pdf_url or pdf_url
    final_url = pub_article_url or url
    final_access_url = final_pdf_url or final_url

    return {
        "id": int(r["id"]),
        "title": _clean_cell(r.get("title")) or "",
        "authors": _format_authors(r.get("authors")) or "",
        "keywords": pub_keywords or _format_keywords(r.get("keywords")),
        "year": int(r["year"]) if pd.notna(r.get("year")) and str(r.get("year")).strip() else None,
        "source": _clean_cell(r.get("source")) or "",
        "journal": pub_journal or _clean_cell(r.get("source")) or "",
        "category": _clean_cell(r.get("category")) or "",
        "abstract": _clean_cell(r.get("abstract")) or "",
        "doi": pub_doi,
        "pdf_url": final_pdf_url,
        "url": final_url,
        "access_url": final_access_url,
        "is_pdf": isinstance(final_access_url, str) and ".pdf" in final_access_url.lower(),
        "similarity_score": 0.0,
    }