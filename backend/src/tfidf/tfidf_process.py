# src/tfidf/tfidf_process.py
from sklearn.feature_extraction.text import TfidfVectorizer
import scipy.sparse as sp
import pickle
import os

def build_tfidf(texts: list, save_dir: str):
    """Fit TF-IDF dan simpan vectorizer + matriks"""
    vectorizer = TfidfVectorizer(
        sublinear_tf=False,
        use_idf=True,
        smooth_idf=False,
        norm='l2',
        min_df=1
    )
    tfidf_matrix = vectorizer.fit_transform(texts)

    os.makedirs(save_dir, exist_ok=True)
    with open(os.path.join(save_dir, 'vectorizer.pkl'), 'wb') as f:
        pickle.dump(vectorizer, f)
    sp.save_npz(os.path.join(save_dir, 'tfidf_matrix.npz'), tfidf_matrix)

    return vectorizer, tfidf_matrix

def load_tfidf(save_dir: str):
    """Load vectorizer + matriks yang sudah disimpan"""
    with open(os.path.join(save_dir, 'vectorizer.pkl'), 'rb') as f:
        vectorizer = pickle.load(f)
    tfidf_matrix = sp.load_npz(os.path.join(save_dir, 'tfidf_matrix.npz'))
    return vectorizer, tfidf_matrix