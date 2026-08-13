# PaperCi (PaperCitation)

**PaperCi** adalah sistem pencarian dan analisis sitasi artikel akademik. Sistem ini membantu peneliti menemukan artikel paling relevan terhadap suatu topik menggunakan metode Information Retrieval, visualisasi jaringan relasi antar artikel, serta manajemen referensi penelitian. Proyek ini dikembangkan sebagai Tugas Akhir.

## Fitur Utama

- **Pencarian Artikel Relevan** — pemeringkatan hasil pencarian berbasis pembobotan **TF-IDF (Term Frequency–Inverse Document Frequency)** dan **Cosine Similarity**.
- **Preprocessing Teks Bahasa Indonesia** — pipeline cleaning (lowercase, hapus URL/non-alfanumerik), tokenisasi, penghapusan stopword, dan stemming menggunakan **Sastrawi**.
- **Scraping Otomatis** — pengambilan metadata artikel baru dari Google Scholar jika artikel belum tersedia di dataset.
- **Visualisasi Jaringan Sitasi** — analisis relasi antar artikel melalui:
  - *Bibliographic Coupling* (kesamaan referensi)
  - *Keyword Co-occurrence* (kesamaan kata kunci)
  - *Co-authorship* (kesamaan penulis)
- **Manajemen Referensi** — simpan artikel favorit dan riwayat pencarian.
- **Dashboard Statistik** — ringkasan data publikasi, kategori, dan hasil cosine similarity.
- **Manajemen Pengguna & Log Aktivitas** — peran pengguna biasa dan *super admin* (kelola pengguna, publikasi, dan log aktivitas).

## Struktur Proyek

```
backend/                  API server (Python/Flask)
  app/
    routes/               Blueprint endpoint API (auth, search, publikasi, admin)
    services/             Logika bisnis: IR pipeline, ekstraksi, sitasi/SNA, dll.
    models/               Model data
    search_engine.py      Mesin pencarian (TF-IDF + Cosine Similarity)
    db.py                 Koneksi Supabase
  src/
    preprocessing/        Cleaning, tokenisasi, stopword, stemming
    preprocessing_qery/   Preprocessing untuk query pengguna
    scraper/              Scraping Google Scholar & ekstraksi PDF/HTML
    config/               Settings & client Supabase
  data/                   Dataset & hasil eksperimen (CSV, TF-IDF, evaluasi)
  notebooks/              Jupyter notebook riset (preprocessing, TF-IDF, cosine, evaluasi)
  pdfs/                   Kumpulan file PDF artikel
  main.py                 Entry point API server
  main_scrape.py          Script scraping mandiri
frontend/                 SPA frontend (React + TypeScript + Vite)
  src/
    pages/                Landing, dashboard, search, detail, favorite, citation graph, super-admin
    components/           Komponen UI (shadcn/ui) & fitur
    api/api.ts            Koneksi ke backend (BASE_URL http://127.0.0.1:5000/api)
  package.json            Dependensi & script npm
pdfs/                     Kumpulan PDF artikel pendukung
scripts/                  Script pendukung (pembuatan dokumen revisi)
```

## Tech Stack

| Lapisan   | Teknologi                                                                  |
| --------- | -------------------------------------------------------------------------- |
| Backend   | Python, Flask, Flask-JWT-Extended, Flask-CORS, Supabase (Postgres), scikit-learn, pandas, numpy, Sastrawi, networkx, pdfplumber, trafilatura |
| Frontend  | React 19, TypeScript, Vite, TailwindCSS v4, shadcn/ui, recharts, d3, framer-motion, react-router-dom |
| Lainnya   | Google Scholar, OpenAlex, Jupyter Notebook                                  |

## Prasyarat

- **Python 3.x** (disarankan 3.10+)
- **Node.js** dan **npm**
- **Project Supabase** — siapkan `.env` di `backend/` dengan variabel:

  ```
  SUPABASE_URL=
  SUPABASE_KEY=
  SUPABASE_SERVICE_ROLE_KEY=
  SECRET_KEY=
  SMTP_HOST=
  SMTP_PORT=
  SMTP_USER=
  SMTP_PASS=
  MAIL_FROM=
  MAIL_TO=
  ```

## Cara Menjalankan

### 1. Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux
pip install -r requirements.txt
```

Isi file `.env` sesuai konfigurasi Supabase, lalu jalankan server:

```bash
python main.py
```

API berjalan di `http://127.0.0.1:5000` (prefix endpoint: `/api`).

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Aplikasi berjalan di `http://localhost:5173`. Koneksi ke backend dikonfigurasi di `frontend/src/api/api.ts`.

### 3. Scraping Mandiri (Opsional)

Menjalankan scraping dari terminal tanpa melalui antarmuka web:

```bash
cd backend
python main_scrape.py
```

## API Endpoints

| Metode | Endpoint                        | Deskripsi                                  |
| ------ | ------------------------------- | ------------------------------------------ |
| POST   | `/api/auth/register`            | Registrasi pengguna baru                   |
| POST   | `/api/auth/login`               | Login pengguna                             |
| POST   | `/api/auth/logout`              | Logout pengguna                            |
| PUT    | `/api/auth/profile`             | Perbarui profil pengguna                   |
| GET    | `/api/search`                   | Pencarian artikel (TF-IDF + Cosine)        |
| GET    | `/api/search-progress`          | Progres pencarian real-time (SSE)          |
| GET    | `/api/stats`                    | Statistik publikasi                        |
| GET    | `/api/cosine-results`           | Hasil cosine similarity per query          |
| GET    | `/api/graph-data`               | Data graf jaringan sitasi                  |
| GET    | `/api/categories`               | Daftar kategori artikel                    |
| GET    | `/api/relation-types`           | Daftar tipe relasi analisis                |
| GET    | `/api/publications/...`         | Data publikasi & daftar artikel            |
| GET    | `/api/users`                    | Manajemen pengguna (super admin)           |
| GET    | `/api/admin/publications`       | Manajemen publikasi (super admin)          |
| GET    | `/api/admin/activity-logs`      | Log aktivitas pengguna (super admin)       |

## Research Pipeline

Eksperimen riset terdokumentasi pada `backend/notebooks/`:

- **`preprocessing.ipynb`** — pipeline pembersihan teks (cleaning, tokenisasi, stopword, stemming Sastrawi).
- **`tfidf.ipynb`** — pembangunan kosakata, dokumen berbobot TF-IDF, dan matriks bobot.
- **`cosine.ipynb`** — perhitungan kemiripan antar judul/abstrak (*title vs abstract*) serta skor keseluruhan per kategori.
- **`evaluation.ipynb`** — evaluasi Precision@K dan eksperimen threshold.

Hasil eksperimen tersimpan di `backend/data/`:

- `tfidf/` — kosakata, matriks TF-IDF, bobot kata, term penting per kategori.
- `cosine_results/` — skor similarity per kategori (cyber security, machine learning, mobile application, web application).
- `evaluation/` — ground truth evaluator, tabel hasil pencarian, Precision@K, dan rata-rata per kategori.

## Evaluasi

Evaluasi sistem menggunakan metrik **Precision at K (K=5, 10, 20)** dengan:

- **12 query uji** bilingual (Bahasa Indonesia dan Inggris), masing-masing 3 query per kategori artikel (Machine Learning, Web Application, Cyber Security, Mobile Application).
- **225 pasangan artikel-query** dinilai oleh **3 evaluator independen** (label biner relevan/tidak relevan).
- **Label Final** ditentukan melalui *majority vote* (konsensus minimal 2 dari 3 evaluator)
- Hasil: **196 artikel (87,1%) relevan** dan **29 artikel (12,9%) tidak relevan**.

Details selengkapnya dapat dilihat pada berkas dokumen revisi dan file CSV di `backend/data/evaluation/`.