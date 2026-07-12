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
from src.preprocessing.stopwords import get_stopwords
from src.preprocessing.stemming import stemming

TFIDF_DIR = os.path.join(BASE_DIR, "data", "tfidf")
COSINE_DIR = os.path.join(BASE_DIR, "data", "cosine_results")

RELATION_TYPE_LABELS = {
    "bibliographic_coupling": "Bibliographic Coupling",
    "keyword_cooccurrence": "Keyword Co-occurrence",
    "co_authorship": "Co-authorship",
}


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


def _fetch_relation_rows(relation_type=None):
    rows = []
    offset = 0
    batch_size = 1000

    while True:
        query = (
            supabase.table("article_relations")
            .select("source_id,target_id,relation_type")
            .range(offset, offset + batch_size - 1)
        )
        if relation_type:
            query = query.eq("relation_type", relation_type)

        response = query.execute()
        batch = response.data or []
        if not batch:
            break

        rows.extend(batch)
        offset += batch_size
        if len(batch) < batch_size:
            break

    return rows


def _get_relation_article_ids(relation_type):
    relation_type = str(relation_type or "").strip()
    if not relation_type:
        return set()

    ids = set()
    for row in _fetch_relation_rows(relation_type=relation_type):
        for key in ("source_id", "target_id"):
            try:
                ids.add(int(row.get(key)))
            except (TypeError, ValueError):
                continue

    return ids


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
    base_columns = (
        "id,title,authors,year,source,category,abstract,"
        "pdf_url,url,scrape_status,cleaned_text"
    )
    selected_columns = base_columns + ",keywords,reference_list"

    try:
        rows = _fetch_all_supabase(
            "cleaned_papers_results",
            selected_columns,
        )
    except Exception as error:
        if (
            "keywords" not in str(error).lower()
            and "reference_list" not in str(error).lower()
        ):
            raise
        rows = _fetch_all_supabase(
            "cleaned_papers_results",
            base_columns,
        )

    if not rows:
        raise RuntimeError("Tabel cleaned_papers_results kosong atau gagal diakses.")

    metadata_df = pd.DataFrame(rows)
    metadata_df["id"] = metadata_df["id"].astype("int64")

    required_cols = [
        "id", "title", "authors", "year", "source", "category",
        "abstract", "keywords", "reference_list", "pdf_url", "url",
        "scrape_status", "cleaned_text"
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
        "keywords", "reference_list", "pdf_url", "url", "scrape_status",
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


def _emit_search_progress(progress_callback, payload):
    if callable(progress_callback):
        progress_callback(payload)


def search_articles(
    query,top_k=50,year_start=None,year_end=None,jenis_artikel=None, jenis_analisis=None, jumlah_publikasi=None, jumlah_kemunculan=None, kategori=None, progress_callback=None,):
    _emit_search_progress(progress_callback, {
        "stage": "prepare",
        "event": "start",
        "message": "Menyiapkan dataset artikel dari Supabase...",
        "article_count": int(len(doc_index)),
        "vocab_count": int(tfidf_matrix.shape[1]),
    })
    _emit_search_progress(progress_callback, {
        "stage": "prepare",
        "event": "done",
        "message": f"Dataset siap: {len(doc_index)} artikel",
        "article_count": int(len(doc_index)),
        "vocab_count": int(tfidf_matrix.shape[1]),
    })

    _emit_search_progress(progress_callback, {
        "stage": "preprocessing",
        "event": "start",
        "message": "Membersihkan dan memecah kata kunci pencarian...",
        "query": query,
    })
    query_terms = preprocess_query(query)
    _emit_search_progress(progress_callback, {
        "stage": "preprocessing",
        "event": "done",
        "message": f"Preprocessing selesai: {len(query_terms)} kata kunci dipakai",
        "query_terms": query_terms,
        "term_count": len(query_terms),
    })

    if not query_terms:
        _emit_search_progress(progress_callback, {
            "stage": "final",
            "event": "done",
            "message": "Kata kunci tidak menghasilkan token yang dapat dicari",
            "result_count": 0,
        })
        return {
            "articles": [],
            "total_occurrences": 0,
            "paper_count": 0,
            "total_matched": 0,
            "displayed_count": 0,
            "displayed_occurrences": 0,
        }

    _emit_search_progress(progress_callback, {
        "stage": "tfidf",
        "event": "start",
        "message": "Menghitung bobot TF-IDF untuk kata kunci...",
        "term_count": len(query_terms),
    })
    query_vec = build_query_vector(query_terms)
    non_zero_terms = int(np.count_nonzero(query_vec))
    _emit_search_progress(progress_callback, {
        "stage": "tfidf",
        "event": "done",
        "message": f"Bobot TF-IDF query selesai: {non_zero_terms} term cocok dengan vocabulary",
        "matched_term_count": non_zero_terms,
        "vocab_count": int(tfidf_matrix.shape[1]),
    })

    _emit_search_progress(progress_callback, {
        "stage": "vsm",
        "event": "start",
        "message": "Menyiapkan Vector Space Model dari matriks dataset...",
        "document_count": int(tfidf_matrix.shape[0]),
        "vocab_count": int(tfidf_matrix.shape[1]),
    })
    _emit_search_progress(progress_callback, {
        "stage": "vsm",
        "event": "done",
        "message": f"VSM siap: {tfidf_matrix.shape[0]} dokumen x {tfidf_matrix.shape[1]} term",
        "document_count": int(tfidf_matrix.shape[0]),
        "vocab_count": int(tfidf_matrix.shape[1]),
    })

    _emit_search_progress(progress_callback, {
        "stage": "cosine",
        "event": "start",
        "message": "Menghitung Cosine Similarity antara query dan seluruh artikel...",
        "document_count": int(tfidf_matrix.shape[0]),
    })
    scores = cosine_similarity(query_vec, tfidf_matrix).flatten()
    positive_scores = int(np.count_nonzero(scores > 0))
    _emit_search_progress(progress_callback, {
        "stage": "cosine",
        "event": "done",
        "message": f"Cosine Similarity selesai: {positive_scores} artikel memiliki kecocokan awal",
        "matched_count": positive_scores,
    })

    _emit_search_progress(progress_callback, {
        "stage": "filter",
        "event": "start",
        "message": "Menyaring artikel sesuai kata kunci dan filter yang dipilih...",
    })
    ranked_idx = np.argsort(scores)[::-1]
    results = doc_index.iloc[ranked_idx].copy()
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

    if jenis_analisis is not None and str(jenis_analisis).strip() != "":
        relation_article_ids = _get_relation_article_ids(jenis_analisis)
        if relation_article_ids:
            results = results[results["id"].astype(int).isin(relation_article_ids)]
        else:
            results = results.iloc[0:0]

    results["pdf_url"] = results["pdf_url"].apply(_clean_cell)
    results["url"] = results["url"].apply(_clean_cell)
    results["access_url"] = results.apply( lambda row: row["pdf_url"] if row["pdf_url"] else row["url"], axis=1)    
    results["is_pdf"] = results["access_url"].apply(_is_direct_pdf)

    if jenis_artikel == "open":
        results = results[results["is_pdf"] == True]
    elif jenis_artikel == "close":
        results = results[results["is_pdf"] == False]

    results["term_frequency"] = results["document_text"].apply( lambda text: count_occurrence(text, query_terms))

    if jumlah_kemunculan is not None and str(jumlah_kemunculan).strip() != "":
        min_occ = int(jumlah_kemunculan)
        results = results[results["term_frequency"] >= min_occ]

    if jumlah_publikasi is not None and str(jumlah_publikasi).strip() != "":
        top_k = int(jumlah_publikasi)

    total_matched = int(len(results))
    total_occurrences = int(results["term_frequency"].sum())
    _emit_search_progress(progress_callback, {
        "stage": "filter",
        "event": "done",
        "message": f"Artikel sesuai filter: {total_matched}",
        "matched_count": total_matched,
        "total_occurrences": total_occurrences,
    })

    _emit_search_progress(progress_callback, {
        "stage": "final",
        "event": "start",
        "message": "Menyusun hasil akhir berdasarkan skor kecocokan...",
        "matched_count": total_matched,
        "top_k": int(top_k),
    })

    results = results.head(int(top_k))
    displayed_count = int(len(results))
    displayed_occurrences = int(results["term_frequency"].sum())

    results["occurrence"] = results["term_frequency"]
    results["jenis_analisis"] = jenis_analisis or ""
    results["rank"] = range(1, len(results) + 1)

    results = results.drop(columns=["document_text"], errors="ignore")
    results = results.fillna("")
    _emit_search_progress(progress_callback, {
        "stage": "final",
        "event": "done",
        "message": f"Hasil akhir siap: {displayed_count} artikel ditampilkan",
        "displayed_count": displayed_count,
        "total_matched": total_matched,
        "total_occurrences": total_occurrences,
    })

    return {
        "articles": results.to_dict("records"),
        "total_occurrences": total_occurrences,
        "paper_count": displayed_count,
        "total_matched": total_matched,
        "displayed_count": displayed_count,
        "displayed_occurrences": displayed_occurrences,}


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


def _coerce_bool(value):
    if isinstance(value, bool):
        return value

    if pd.isna(value):
        return False

    return str(value).strip().lower() in ["true", "1", "yes", "y"]


def _cosine_base_dataframe():
    if doc_index.empty or "id" not in doc_index.columns:
        return pd.DataFrame()

    metadata_cols = [
        "id", "title", "authors", "year", "source", "category",
        "abstract", "pdf_url", "url", "scrape_status", "document_text"
    ]
    available_cols = [col for col in metadata_cols if col in doc_index.columns]
    df = doc_index[available_cols].copy()

    df["id"] = pd.to_numeric(df["id"], errors="coerce")
    df = df.dropna(subset=["id"])
    df["id"] = df["id"].astype(int)
    df["category"] = df.get("category", "").fillna("").astype(str).str.strip()
    df = df[df["category"] != ""].copy()

    if df.empty:
        return df

    df["query"] = df["category"]
    df["authors"] = df.get("authors", "").apply(_format_authors)
    df["year"] = pd.to_numeric(df.get("year"), errors="coerce")
    df["similarity_score"] = 0.0
    df["occurrence"] = 0

    for col in ["title", "source", "abstract", "scrape_status", "document_text"]:
        if col not in df.columns:
            df[col] = ""
        df[col] = df[col].fillna("").astype(str).str.strip()

    for category in df["category"].dropna().unique():
        query_terms = preprocess_query(str(category))
        category_mask = df["category"].astype(str).str.lower() == str(category).lower()

        if not query_terms:
            continue

        query_vec = build_query_vector(query_terms)
        scores = cosine_similarity(query_vec, tfidf_matrix).flatten()
        row_positions = df.index[category_mask].to_numpy()

        df.loc[category_mask, "similarity_score"] = scores[row_positions]
        df.loc[category_mask, "occurrence"] = df.loc[
            category_mask, "document_text"
        ].apply(lambda text: count_occurrence(text, query_terms))

    df = df.sort_values(
        ["query", "similarity_score", "id"],
        ascending=[True, False, True]
    )
    df["rank"] = df.groupby("query").cumcount() + 1

    df["interpretation"] = np.select(
        [
            df["similarity_score"] >= 0.45,
            df["similarity_score"] >= 0.20,
            df["similarity_score"] > 0,
        ],
        ["Relevan Tinggi", "Relevan Sedang", "Relevan Rendah"],
        default="Tidak Relevan"
    )

    for col in ["pdf_url", "url", "access_url"]:
        if col not in df.columns:
            df[col] = None
        df[col] = df[col].apply(_clean_cell)

    df["access_url"] = df.apply(
        lambda row: row["access_url"] or row["pdf_url"] or row["url"],
        axis=1
    )

    if "is_pdf" in df.columns:
        df["is_pdf"] = df["is_pdf"].apply(_coerce_bool)
    else:
        df["is_pdf"] = False

    df["is_pdf"] = df.apply(
        lambda row: bool(row["is_pdf"]) or _is_direct_pdf(row["access_url"]),
        axis=1
    )

    df = df.drop(columns=["document_text"], errors="ignore")

    return df


def get_cosine_catalog(
    query=None,
    kategori=None,
    year_start=None,
    year_end=None,
    jenis_artikel=None,
    sort_by="query_rank",
):
    base_df = _cosine_base_dataframe()

    if base_df.empty:
        return {
            "articles": [],
            "total": 0,
            "total_all": 0,
            "queries": [],
            "categories": [],
        }

    query_options = [
        {"value": value, "label": value.title(), "count": int(count)}
        for value, count in base_df["query"].value_counts().sort_index().items()
    ]
    category_options = [
        {"value": value, "label": value, "count": int(count)}
        for value, count in base_df["category"].value_counts().sort_index().items()
        if str(value).strip()
    ]

    df = base_df.copy()

    if query is not None and str(query).strip() != "":
        selected_query = str(query).strip().lower()
        df = df[df["query"].str.lower() == selected_query]

    if kategori is not None and str(kategori).strip() != "":
        selected_category = str(kategori).strip().lower()
        df = df[df["category"].str.lower() == selected_category]

    if year_start is not None and str(year_start).strip() != "":
        df = df[df["year"] >= int(year_start)]

    if year_end is not None and str(year_end).strip() != "":
        df = df[df["year"] <= int(year_end)]

    if jenis_artikel == "open":
        df = df[df["is_pdf"] == True]
    elif jenis_artikel == "close":
        df = df[df["is_pdf"] == False]

    if sort_by == "similarity_asc":
        df = df.sort_values(["similarity_score", "query"], ascending=[True, True])
    elif sort_by == "year_desc":
        df = df.sort_values(["year", "similarity_score"], ascending=[False, False])
    elif sort_by == "year_asc":
        df = df.sort_values(["year", "similarity_score"], ascending=[True, False])
    elif sort_by == "similarity_desc":
        df = df.sort_values(["similarity_score", "query"], ascending=[False, True])
    else:
        df = df.sort_values(["query", "rank", "similarity_score"], ascending=[True, True, False])

    columns = [
        "id", "query", "rank", "title", "authors", "year", "source",
        "category", "abstract", "similarity_score", "occurrence",
        "interpretation", "pdf_url", "url", "access_url", "is_pdf",
        "scrape_status"
    ]

    for col in columns:
        if col not in df.columns:
            df[col] = None

    df = df[columns].copy()
    df["rank"] = df["rank"].where(pd.notna(df["rank"]), None)
    df["year"] = df["year"].where(pd.notna(df["year"]), None)

    records = []
    for record in df.replace({np.nan: None}).to_dict("records"):
        if record.get("rank") is not None:
            record["rank"] = int(record["rank"])
        if record.get("year") is not None:
            record["year"] = int(record["year"])
        record["id"] = int(record["id"])
        record["similarity_score"] = float(record.get("similarity_score") or 0)
        record["occurrence"] = int(record.get("occurrence") or 0)
        record["is_pdf"] = bool(record.get("is_pdf"))
        records.append(record)

    return {
        "articles": records,
        "total": len(records),
        "total_all": int(len(base_df)),
        "queries": query_options,
        "categories": category_options,
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


def get_relation_type_options():
    counts = Counter()

    for row in _fetch_relation_rows():
        relation_type = str(row.get("relation_type") or "").strip()
        if relation_type:
            counts[relation_type] += 1

    return [
        {
            "value": relation_type,
            "label": RELATION_TYPE_LABELS.get(
                relation_type,
                relation_type.replace("_", " ").title(),
            ),
            "count": int(count),
        }
        for relation_type, count in sorted(counts.items())
    ]


def get_article_by_id(article_id: int):
    selected_columns = (
        "id,title,authors,year,source,category,abstract,doi,"
        "keywords,reference_list,pdf_url,url,scrape_status"
    )

    try:
        response = (
            supabase.table("cleaned_papers_results")
            .select(selected_columns)
            .eq("id", article_id)
            .limit(1)
            .execute()
        )
    except Exception as error:
        if "doi" not in str(error).lower():
            raise
        response = (
            supabase.table("cleaned_papers_results")
            .select(
                "id,title,authors,year,source,category,abstract,"
                "keywords,reference_list,pdf_url,url,scrape_status"
            )
            .eq("id", article_id)
            .limit(1)
            .execute()
        )

    if not response.data:
        return None

    r = response.data[0]

    pdf_url = _clean_cell(r.get("pdf_url"))
    url = _clean_cell(r.get("url"))
    # access_url = pdf_url if pdf_url else url

    final_pdf_url = pdf_url
    final_url = url
    final_access_url = final_pdf_url or final_url

    return {
        "id": int(r.get("id")),
        "title": _clean_cell(r.get("title")) or "",
        "authors": _format_authors(r.get("authors")) or "",
        "keywords": _format_keywords(r.get("keywords")),
        "reference_list": _format_keywords(r.get("reference_list")),
        "year": int(r["year"]) if r.get("year") is not None and str(r.get("year")).strip() else None,
        "source": _clean_cell(r.get("source")) or "",
        "journal": _clean_cell(r.get("source")) or "",
        "category": _clean_cell(r.get("category")) or "",
        "abstract": _clean_cell(r.get("abstract")) or "",
        "doi": _clean_cell(r.get("doi")),
        "pdf_url": final_pdf_url,
        "url": final_url,
        "access_url": final_access_url,
        "is_pdf": isinstance(final_access_url, str) and ".pdf" in final_access_url.lower(),
        "similarity_score": 0.0,
    }
