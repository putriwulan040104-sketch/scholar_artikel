import os, sys, pickle, glob
import numpy as np
import pandas as pd
import scipy.sparse as sp
from sklearn.metrics.pairwise import cosine_similarity

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT_DIR = os.path.dirname(BASE_DIR)
sys.path.insert(0, ROOT_DIR)
sys.path.insert(0, BASE_DIR)

from src.preprocessing.clean_text import clean_text
from src.preprocessing.casefolding import casefolding
from src.preprocessing.tokenizing import tokenizing
from src.preprocessing.stopwords_id import get_stopwords
from src.preprocessing.stemming import stemming

TFIDF_DIR  = os.path.join(BASE_DIR, 'data', 'tfidf')
CSV_PATH   = os.path.join(BASE_DIR, 'data', 'cleaned_papers.csv')
COSINE_DIR = os.path.join(BASE_DIR, 'data', 'cosine_results')

doc_index = pd.read_csv(CSV_PATH)

cosine_files = glob.glob(os.path.join(COSINE_DIR, 'similarity_score_*.csv'))
if cosine_files:
    cosine_dfs = []
    for f in cosine_files:
        df         = pd.read_csv(f)
        query_name = os.path.basename(f).replace('similarity_score_', '').replace('.csv', '').replace('_', ' ')
        df['query'] = query_name
        cosine_dfs.append(df)
    cosine_results = pd.concat(cosine_dfs, ignore_index=True)
else:
    cosine_results = pd.DataFrame()

with open(os.path.join(TFIDF_DIR, 'vectorizer.pkl'), 'rb') as f:
    vectorizer = pickle.load(f)

tfidf_matrix = sp.load_npz(os.path.join(TFIDF_DIR, 'tfidf_matrix.npz'))
stop_words   = get_stopwords()

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

print(f'✅ Model loaded: {len(doc_index)} dokumen, vocab {tfidf_matrix.shape[1]} term')

def preprocess_query(query: str) -> str:
    text   = clean_text(query)
    text   = casefolding(text)
    tokens = tokenizing(text)
    tokens = [t for t in tokens if t not in stop_words and len(t) > 1]
    if all(token.isascii() for token in tokens):
        return ' '.join(tokens)
    return ' '.join(stemming(tokens))

SUMBER_MAP = {
    "scopus"   : "Scopus",
    "wos"      : "Web of Science",
    "semantic" : "Semantic Scholar",
    "crossref" : "CrossRef",
}

def search_articles(
    query,
    top_k             = 10,
    year_start        = None,
    year_end          = None,
    jenis_artikel     = None,
    jenis_analisis    = None,
    jumlah_publikasi  = None,
    jumlah_kemunculan = None,
    sumber_data       = None,
):
    processed  = preprocess_query(query)
    query_vec  = vectorizer.transform([processed])
    scores     = cosine_similarity(query_vec, tfidf_matrix).flatten()
    ranked_idx = np.argsort(scores)[::-1]

    results = doc_index.iloc[ranked_idx][[
        'id', 'title', 'authors', 'year',
        'source', 'category', 'abstract',
        'pdf_url', 'url'
    ]].copy()

    results['similarity_score'] = scores[ranked_idx]
    results = results[results['similarity_score'] > 0].reset_index(drop=True)

    if year_start:
        results = results[results['year'] >= int(year_start)]
    if year_end:
        results = results[results['year'] <= int(year_end)]

    if sumber_data and sumber_data in SUMBER_MAP:
        label = SUMBER_MAP[sumber_data]
        mask  = results['source'].str.lower().str.contains(label.lower(), na=False)
        if mask.any():
            results = results[mask]

    if jenis_artikel == "open":
        results = results[results['pdf_url'].notna() & (results['pdf_url'] != "")]
    elif jenis_artikel == "close":
        results = results[results['pdf_url'].isna() | (results['pdf_url'] == "")]

    if jumlah_kemunculan and 'cited_by' in results.columns:
        results = results[results['cited_by'] >= int(jumlah_kemunculan)]

    if jumlah_publikasi:
        top_k = int(jumlah_publikasi)

    results = results.head(top_k)

    def clean(val):
        if pd.isna(val):
            return None
        val = str(val).strip()
        if val.lower() in ["", "nan", "none", "null"]:
            return None
        return val

    results['pdf_url'] = results['pdf_url'].apply(clean)
    results['url']     = results['url'].apply(clean)

    results['access_url'] = results.apply(
        lambda r: r['pdf_url'] if r['pdf_url'] else r['url'],
        axis=1
    )
    results['is_pdf'] = results['access_url'].apply(
        lambda x: isinstance(x, str) and ".pdf" in x.lower()
    )

    results['jenis_analisis'] = jenis_analisis or ""
    results['rank'] = range(1, len(results) + 1)
    results = results.fillna("")

    return results.to_dict('records')


def get_stats():
    kemunculan = {}
    if not cosine_results.empty and 'title' in cosine_results.columns:
        kemunculan = cosine_results['title'].value_counts().head(10).to_dict()

    return {
        'total_artikel' : len(doc_index),
        'total_sumber'  : int(doc_index['source'].nunique()),
        'per_tahun'     : {int(k): int(v) for k, v in
                        doc_index['year'].value_counts().sort_index().items()},
        'per_kategori'  : {k: int(v) for k, v in
                        doc_index['category'].value_counts().items()},
        'top_kemunculan': kemunculan,
    }
def get_article_by_id(article_id: int):
    """Ambil artikel langsung dari CSV berdasarkan ID, tanpa search."""
    row = doc_index[doc_index['id'] == article_id]
    
    if row.empty:
        return None
    
    def clean(val):
        if pd.isna(val):
            return None
        val = str(val).strip()
        if val.lower() in ["", "nan", "none", "null"]:
            return None
        return val

    r = row.iloc[0]
    
    pdf_url    = clean(r.get('pdf_url'))
    url        = clean(r.get('url'))
    access_url = pdf_url if pdf_url else url

    return {
        'id'               : int(r['id']),
        'title'            : clean(r['title']) or "",
        'authors'          : clean(r['authors']) or "",
        'year'             : int(r['year']) if pd.notna(r.get('year')) else None,
        'source'           : clean(r.get('source')) or "",
        'category'         : clean(r.get('category')) or "",
        'abstract'         : clean(r.get('abstract')) or "",
        'pdf_url'          : pdf_url,
        'url'              : url,
        'access_url'       : access_url,
        'is_pdf'           : isinstance(access_url, str) and ".pdf" in access_url.lower(),
        'similarity_score' : 0.0,  # tidak relevan untuk detail langsung
    }
