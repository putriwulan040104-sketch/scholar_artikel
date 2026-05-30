import os
import sys
import ast
import glob
import pickle
import numpy as np
import pandas as pd
import scipy.sparse as sp
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

    # Handle stringified list: "['A', 'B']"
    if s.startswith("[") and s.endswith("]"):
        try:
            arr = ast.literal_eval(s)
            if isinstance(arr, list):
                cleaned = [str(x).strip() for x in arr if str(x).strip()]
                return ", ".join(cleaned)
        except Exception:
            pass

    return s


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


def _load_doc_index_from_supabase():
    res = (
        supabase.table("cleaned_papers_results")
        .select("id,title,authors,year,source,category,abstract,pdf_url,url,scrape_status,cleaned_text")
        .order("id")
        .execute()
    )

    rows = res.data or []
    if not rows:
        raise RuntimeError("Tabel cleaned_papers_results kosong atau gagal diakses.")

    df = pd.DataFrame(rows)

    # Pastikan kolom wajib ada
    required_cols = [
        "id", "title", "authors", "year",
        "source", "category", "abstract",
        "pdf_url", "url", "scrape_status"
    ]
    for c in required_cols:
        if c not in df.columns:
            df[c] = None

    # Normalisasi author untuk display
    df["authors"] = df["authors"].apply(_format_authors)

    return df


doc_index = _load_doc_index_from_supabase()

cosine_files = glob.glob(os.path.join(COSINE_DIR, "similarity_score_*.csv"))
if cosine_files:
    cosine_dfs = []
    for f in cosine_files:
        df = pd.read_csv(f)
        query_name = (
            os.path.basename(f)
            .replace("similarity_score_", "")
            .replace(".csv", "")
            .replace("_", " ")
        )
        df["query"] = query_name
        cosine_dfs.append(df)
    cosine_results = pd.concat(cosine_dfs, ignore_index=True)
else:
    cosine_results = pd.DataFrame()

with open(os.path.join(TFIDF_DIR, "vectorizer.pkl"), "rb") as f:
    vectorizer = pickle.load(f)

tfidf_matrix = sp.load_npz(os.path.join(TFIDF_DIR, "tfidf_matrix.npz"))
stop_words = get_stopwords()

if len(doc_index) != tfidf_matrix.shape[0]:
    raise RuntimeError(
        f"Jumlah data Supabase ({len(doc_index)}) != baris tfidf_matrix ({tfidf_matrix.shape[0]}). "
        "Rebuild TF-IDF dari dataset Supabase yang sama, atau samakan urutan/datanya."
    )

print(f"✅ Model loaded: {len(doc_index)} dokumen, vocab {tfidf_matrix.shape[1]} term")


def preprocess_query(query: str) -> str:
    text = clean_text(query)
    tokens = tokenizing(text)
    tokens = [t for t in tokens if t not in stop_words and len(t) > 1]
    if all(token.isascii() for token in tokens):
        return " ".join(tokens)
    return " ".join(stemming(tokens))


SUMBER_MAP = {
    "scopus": "Scopus",
    "wos": "Web of Science",
    "semantic": "Semantic Scholar",
    "crossref": "CrossRef",
}


def search_articles(
    query,
    top_k=10,
    year_start=None,
    year_end=None,
    jenis_artikel=None,
    jenis_analisis=None,
    jumlah_publikasi=None,
    jumlah_kemunculan=None,
    sumber_data=None,
):
    processed = preprocess_query(query)
    query_terms = processed.split()

    query_vec = vectorizer.transform([processed])
    scores = cosine_similarity(query_vec, tfidf_matrix).flatten()
    ranked_idx = np.argsort(scores)[::-1]

    results = doc_index.iloc[ranked_idx][[
        "id", "title", "authors", "year",
        "source", "category", "abstract",
        "pdf_url", "url", "scrape_status"
    ]].copy()

    results["similarity_score"] = scores[ranked_idx]
    results = results[results["similarity_score"] > 0].reset_index(drop=True)

    if year_start is not None and str(year_start).strip() != "":
        results = results[results["year"] >= int(year_start)]
    if year_end is not None and str(year_end).strip() != "":
        results = results[results["year"] <= int(year_end)]

    if sumber_data and sumber_data in SUMBER_MAP:
        label = SUMBER_MAP[sumber_data]
        mask = results["source"].astype(str).str.lower().str.contains(label.lower(), na=False)
        if mask.any():
            results = results[mask]

    # URL clean
    results["pdf_url"] = results["pdf_url"].apply(_clean_cell)
    results["url"] = results["url"].apply(_clean_cell)

    # access_url + status PDF
    results["access_url"] = results.apply(
        lambda r: r["pdf_url"] if r["pdf_url"] else r["url"],
        axis=1
    )
    results["is_pdf"] = results["access_url"].apply(_is_direct_pdf)

    # filter jenis artikel
    if jenis_artikel == "open":
        results = results[results["is_pdf"] == True]
    elif jenis_artikel == "close":
        results = results[results["is_pdf"] == False]

    # jumlah kemunculan (term frequency)
    def count_tf(text):
        tokens = str(text).lower().split()
        return sum(tokens.count(t) for t in query_terms)

    results["term_frequency"] = results["abstract"].apply(count_tf)

    if jumlah_kemunculan is not None and str(jumlah_kemunculan).strip() != "":
        min_occ = int(jumlah_kemunculan)
        results = results[results["term_frequency"] >= min_occ]

    if jumlah_publikasi is not None and str(jumlah_publikasi).strip() != "":
        top_k = int(jumlah_publikasi)

    # Total hasil query setelah semua filter, sebelum dipotong top_k
    total_matched = int(len(results))
    total_occurrences = int(results["term_frequency"].sum())

    results = results.head(int(top_k))
    displayed_count = int(len(results))
    displayed_occurrences = int(results["term_frequency"].sum())

    results["occurrence"] = results["term_frequency"]
    results["jenis_analisis"] = jenis_analisis or ""
    results["rank"] = range(1, len(results) + 1)
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
        per_tahun = {
            int(k): int(v)
            for k, v in doc_index["year"].value_counts().sort_index().items()
            if pd.notna(k)
        }

    per_kategori = {}
    if "category" in doc_index.columns:
        per_kategori = {
            str(k): int(v)
            for k, v in doc_index["category"].value_counts().items()
            if pd.notna(k)
        }

    total_sumber = int(doc_index["source"].nunique()) if "source" in doc_index.columns else 0

    return {
        "total_artikel": int(len(doc_index)),
        "total_sumber": total_sumber,
        "per_tahun": per_tahun,
        "per_kategori": per_kategori,
        "top_kemunculan": kemunculan,
    }


def get_article_by_id(article_id: int):
    row = doc_index[doc_index["id"] == article_id]
    if row.empty:
        return None

    r = row.iloc[0]

    pdf_url = _clean_cell(r.get("pdf_url"))
    url = _clean_cell(r.get("url"))
    access_url = pdf_url if pdf_url else url

    return {
        "id": int(r["id"]),
        "title": _clean_cell(r.get("title")) or "",
        "authors": _format_authors(r.get("authors")) or "",
        "year": int(r["year"]) if pd.notna(r.get("year")) else None,
        "source": _clean_cell(r.get("source")) or "",
        "category": _clean_cell(r.get("category")) or "",
        "abstract": _clean_cell(r.get("abstract")) or "",
        "pdf_url": pdf_url,
        "url": url,
        "access_url": access_url,
        "is_pdf": isinstance(access_url, str) and ".pdf" in access_url.lower(),
        "similarity_score": 0.0,
    }
