# src/tfidf/cosine_similarity.py
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import pickle
import scipy.sparse as sp
import pandas as pd
import os

def load_tfidf(save_dir: str):
    """Load vectorizer + matriks TF-IDF"""
    with open(os.path.join(save_dir, 'vectorizer.pkl'), 'rb') as f:
        vectorizer = pickle.load(f)
    tfidf_matrix = sp.load_npz(os.path.join(save_dir, 'tfidf_matrix.npz'))
    return vectorizer, tfidf_matrix

def search(query: str, vectorizer, tfidf_matrix, doc_index: pd.DataFrame, top_k: int = 10):
    """
    Hitung cosine similarity antara query dan semua dokumen
    Return top-K dokumen paling relevan
    """
    # Transformasi query ke vektor TF-IDF
    query_vector = vectorizer.transform([query])
    
    # Hitung cosine similarity
    scores = cosine_similarity(query_vector, tfidf_matrix).flatten()
    
    # Urutkan berdasarkan skor tertinggi
    ranked_indices = np.argsort(scores)[::-1][:top_k]
    
    # Ambil hasil
    results = doc_index.iloc[ranked_indices].copy()
    results['similarity_score'] = scores[ranked_indices]
    results = results[results['similarity_score'] > 0].reset_index(drop=True)
    results.index += 1  # ranking mulai dari 1
    
    return results