# src/preprocessing/stopwords_id.py
STOPWORDS_ID = {
    "yang", "dan", "di", "dari", "untuk", "pada", "dengan", "ini", "itu", "dalam",
    "adalah", "sebagai", "oleh", "atau", "juga", "ke", "karena", "akan", "tetapi",
    "namun", "serta", "sedangkan", "bahwa", "bagi", "antara", "setelah", "sebelum",
    "sampai", "selama", "sudah", "belum", "bisa", "dapat", "harus", "perlu", "lebih",
    "hanya", "saja", "tidak", "ada", "suatu", "mereka", "kami", "kita", "anda",
    "dia", "ia", "aku", "kamu", "kalian", "semua", "beberapa", "banyak", "lain",
    # Tambahkan lagi jika perlu
}

def get_stopwords() -> set:
    return STOPWORDS_ID.copy()