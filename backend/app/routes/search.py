from flask import Blueprint, jsonify, request
import pandas as pd
import os
import glob

search_bp = Blueprint("search", __name__)

# Path ke folder cosine_results (pakai absolut path)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
COSINE_DIR = os.path.join(BASE_DIR, "data", "cosine_results")

@search_bp.route("/results")
def results():
    # Baca semua CSV di folder cosine_results lalu gabungkan
    all_files = glob.glob(os.path.join(COSINE_DIR, "*.csv"))
    
    if not all_files:
        return jsonify({"error": "No CSV files found"}), 404
    
    df_list = [pd.read_csv(f) for f in all_files]
    df = pd.concat(df_list, ignore_index=True)
    
    return jsonify(df.to_dict(orient="records"))