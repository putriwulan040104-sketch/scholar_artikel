from app.search_engine import search_articles, get_category_options
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

@search_bp.route("/categories", methods=["GET"])  # /api/search/categories
def categories():
    return jsonify({
        "status": "success",
        "data": get_category_options(),
    })

@search_bp.route("", methods=["GET"])  # /api/search
def search():
    query = request.args.get("query", "").strip()
    if not query:
        return jsonify({"status": "error", "message": "Query wajib diisi"}), 400

    top_k = request.args.get("top_k", 10, type=int)
    year_start = request.args.get("year_start")
    year_end = request.args.get("year_end")
    jenis_artikel = request.args.get("jenis_artikel")
    jenis_analisis = request.args.get("jenis_analisis")
    jumlah_publikasi = request.args.get("jumlah_publikasi")
    kategori = request.args.get("kategori")

    jumlah_kemunculan = (
        request.args.get("jumlah_kemunculan")
        or request.args.get("jumlahKemunculan")
    )

    result = search_articles(
        query=query,
        top_k=top_k,
        year_start=year_start,
        year_end=year_end,
        jenis_artikel=jenis_artikel,
        jenis_analisis=jenis_analisis,
        jumlah_kemunculan=jumlah_kemunculan,
        jumlah_publikasi=jumlah_publikasi,
        kategori=kategori,
    )

    return jsonify({
        "status": "success",
        "total": result.get("total_matched", len(result["articles"])),
        "total_matched": result.get("total_matched", len(result["articles"])),
        "displayed_count": result.get("displayed_count", len(result["articles"])),
        "data": result["articles"],
        "total_occurrences": result["total_occurrences"],
        "paper_count": result["paper_count"],
    })
