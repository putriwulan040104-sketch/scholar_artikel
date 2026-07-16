import json
import math
import os
from collections import Counter
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import scipy.sparse as sp

from app.db import supabase
from src.preprocessing.clean_text import clean_text
from src.preprocessing.stemming import stemming
from src.preprocessing.stopwords import get_stopwords
from src.preprocessing.tokenizing import tokenizing


BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TFIDF_DIR = os.path.join(BASE_DIR, "data", "tfidf")
SOURCE_TABLE = "scholar_article_doi"
CLEANED_TABLE = "cleaned_papers_results"


def _emit(progress_callback, payload):
    if callable(progress_callback):
        progress_callback(payload)


def _fetch_all(table_name, selected_columns="*", batch_size=1000):
    rows = []
    offset = 0
    while True:
        response = (
            supabase.table(table_name)
            .select(selected_columns)
            .range(offset, offset + batch_size - 1)
            .execute()
        )
        batch = response.data or []
        if not batch:
            break
        rows.extend(batch)
        if len(batch) < batch_size:
            break
        offset += batch_size
    return rows


def _sanitize(value):
    if isinstance(value, str):
        return value.replace("\x00", "")
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if isinstance(value, dict):
        return {key: _sanitize(item) for key, item in value.items()}
    return value


def preprocess_text_to_tokens(text):
    cleaned = clean_text(text)
    tokens = tokenizing(cleaned)
    stop_words = get_stopwords()
    tokens = [token for token in tokens if token not in stop_words and len(token) > 1]
    return stemming(tokens)


def build_document_text(row):
    return f"{row.get('title') or ''} {row.get('abstract') or ''}"


def _source_to_cleaned_row(row):
    title_tokens = preprocess_text_to_tokens(row.get("title") or "")
    abstract_tokens = preprocess_text_to_tokens(row.get("abstract") or "")
    document_tokens = title_tokens + abstract_tokens

    return _sanitize({
        "id": row.get("id"),
        "title": row.get("title") or "",
        "authors": row.get("authors") or "",
        "year": row.get("year"),
        "source": row.get("source") or "",
        "category": row.get("category") or "",
        "abstract": row.get("abstract") or "",
        "pdf_url": row.get("pdf_url"),
        "url": row.get("url"),
        "scrape_status": row.get("scrape_status") or "",
        "cleaned_text": " ".join(document_tokens),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    })


def _upsert_batches(table_name, records, on_conflict="id", batch_size=500):
    if not records:
        return 0

    total = 0
    for start in range(0, len(records), batch_size):
        batch = records[start:start + batch_size]
        supabase.table(table_name).upsert(
            batch,
            on_conflict=on_conflict,
        ).execute()
        total += len(batch)
    return total


def sync_cleaned_dataset_from_final(source_ids=None, progress_callback=None):
    """Menyalin Final Dataset ke cleaned_papers_results secara incremental."""
    _emit(progress_callback, {
        "stage": "preprocessing",
        "event": "start",
        "message": "Menjalankan preprocessing Final Dataset...",
    })

    if source_ids:
        clean_ids = sorted({int(source_id) for source_id in source_ids if source_id is not None})
        if not clean_ids:
            return {"upserted": 0}
        source_rows = (
            supabase.table(SOURCE_TABLE)
            .select("*")
            .in_("id", clean_ids)
            .execute()
            .data
            or []
        )
    else:
        source_rows = _fetch_all(SOURCE_TABLE, "*")

    records = [
        _source_to_cleaned_row(row)
        for row in source_rows
        if row.get("id") is not None
    ]
    upserted = _upsert_batches(CLEANED_TABLE, records, on_conflict="id")

    _emit(progress_callback, {
        "stage": "preprocessing",
        "event": "done",
        "message": f"Preprocessing selesai: {upserted} artikel tersinkronisasi",
        "article_count": upserted,
    })
    return {"upserted": upserted}


def _prepare_tfidf_documents(cleaned_rows):
    docs = []
    for row in cleaned_rows:
        title_tokens = preprocess_text_to_tokens(row.get("title") or "")
        abstract_tokens = preprocess_text_to_tokens(row.get("abstract") or "")
        document_tokens = title_tokens + abstract_tokens
        docs.append({
            "id": int(row.get("id")),
            "title": row.get("title") or "",
            "abstract": row.get("abstract") or "",
            "title_tokens": title_tokens,
            "abstract_tokens": abstract_tokens,
            "document_tokens": document_tokens,
            "document_text": " ".join(document_tokens),
        })
    return docs


def rebuild_tfidf_index(progress_callback=None):
    """Membangun ulang file TF-IDF dan VSM dari cleaned_papers_results."""
    os.makedirs(TFIDF_DIR, exist_ok=True)

    _emit(progress_callback, {
        "stage": "tfidf",
        "event": "start",
        "message": "Mengambil Final Dataset untuk perhitungan TF-IDF...",
    })
    cleaned_rows = _fetch_all(CLEANED_TABLE, "*")
    if not cleaned_rows:
        raise RuntimeError("Tabel cleaned_papers_results kosong, TF-IDF tidak dapat dibangun.")

    documents = _prepare_tfidf_documents(cleaned_rows)
    documents = [doc for doc in documents if doc["id"] is not None]
    documents.sort(key=lambda item: item["id"])
    doc_ids = [doc["id"] for doc in documents]
    doc_count = len(documents)

    doc_term_sets = [set(doc["document_tokens"]) for doc in documents]
    all_terms = sorted({term for term_set in doc_term_sets for term in term_set})
    term_to_index = {term: index for index, term in enumerate(all_terms)}
    doc_freq = {
        term: sum(1 for term_set in doc_term_sets if term in term_set)
        for term in all_terms
    }
    idf_scores = {
        term: math.log10(doc_count / df) if df else 0.0
        for term, df in doc_freq.items()
    }

    _emit(progress_callback, {
        "stage": "tfidf",
        "event": "done",
        "message": f"TF-IDF siap dihitung: {doc_count} dokumen, {len(all_terms)} term",
        "document_count": doc_count,
        "vocab_count": len(all_terms),
    })
    _emit(progress_callback, {
        "stage": "vsm",
        "event": "start",
        "message": "Membangun Vector Space Model...",
        "document_count": doc_count,
        "vocab_count": len(all_terms),
    })

    rows = []
    cols = []
    values = []
    tfidf_records = []
    tfidf_detail_records = []

    for row_index, doc in enumerate(documents):
        tokens = doc["document_tokens"]
        token_count = len(tokens)
        if not token_count:
            continue

        term_counts = Counter(tokens)
        for term, count in sorted(term_counts.items()):
            col_index = term_to_index[term]
            tf = count / token_count
            idf = idf_scores[term]
            tfidf_score = tf * idf

            rows.append(row_index)
            cols.append(col_index)
            values.append(tfidf_score)
            record = {
                "doc_id": doc["id"],
                "term": term,
                "tfidf_score": float(tfidf_score),
            }
            tfidf_records.append(record)
            tfidf_detail_records.append({
                **record,
                "tf": float(tf),
                "df": int(doc_freq[term]),
                "idf": float(idf),
                "term_count": int(count),
                "total_terms": int(token_count),
            })

    tfidf_matrix = sp.csr_matrix(
        (values, (rows, cols)),
        shape=(doc_count, len(all_terms)),
        dtype=float,
    )

    pd.DataFrame(documents).to_csv(
        os.path.join(TFIDF_DIR, "tfidf_documents.csv"),
        index=False,
    )
    pd.DataFrame(tfidf_records).to_csv(
        os.path.join(TFIDF_DIR, "tfidf_weights.csv"),
        index=False,
    )
    pd.DataFrame(tfidf_detail_records).to_csv(
        os.path.join(TFIDF_DIR, "tfidf_weights_detail.csv"),
        index=False,
    )
    sp.save_npz(os.path.join(TFIDF_DIR, "tfidf_matrix.npz"), tfidf_matrix)

    with open(os.path.join(TFIDF_DIR, "tfidf_terms.json"), "w", encoding="utf-8") as file:
        json.dump(all_terms, file, ensure_ascii=False, indent=2)
    with open(os.path.join(TFIDF_DIR, "tfidf_doc_ids.json"), "w", encoding="utf-8") as file:
        json.dump(doc_ids, file, ensure_ascii=False, indent=2)
    with open(os.path.join(TFIDF_DIR, "idf_scores.json"), "w", encoding="utf-8") as file:
        json.dump(idf_scores, file, ensure_ascii=False, indent=2)

    if len(all_terms) <= 5000:
        readable_df = pd.DataFrame(
            tfidf_matrix.toarray(),
            columns=all_terms,
        )
        readable_df.insert(0, "doc_id", doc_ids)
        readable_df.to_csv(os.path.join(TFIDF_DIR, "vsm_matrix_readable.csv"), index=False)

    _emit(progress_callback, {
        "stage": "vsm",
        "event": "done",
        "message": f"VSM selesai: {tfidf_matrix.shape[0]} dokumen x {tfidf_matrix.shape[1]} term",
        "document_count": int(tfidf_matrix.shape[0]),
        "vocab_count": int(tfidf_matrix.shape[1]),
    })

    return {
        "document_count": int(tfidf_matrix.shape[0]),
        "vocab_count": int(tfidf_matrix.shape[1]),
        "non_zero_count": int(tfidf_matrix.nnz),
    }
