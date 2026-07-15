STOPWORDS_ID = {
    "yang", "dan", "di", "ke", "dari", "ini", "itu", "untuk", "dengan", "pada",
    "adalah", "dalam", "atau", "sebagai", "oleh", "karena", "terhadap", "akan",
    "dapat", "lebih", "juga", "tidak", "ada", "antara", "para", "saat", "telah",
    "menjadi", "yaitu", "yakni", "bahwa", "sebuah", "suatu", "agar", "bagi",
    "tanpa", "setelah", "sebelum", "hingga", "maka", "namun", "serta", "tetapi",
    "sedangkan", "sampai", "selama", "sudah", "belum", "bisa", "harus", "perlu",
    "hanya", "saja", "mereka", "kami", "kita", "anda", "dia", "ia", "aku", "kamu",
    "kalian", "semua", "beberapa", "banyak", "lain",
}

STOPWORDS_EN = {
    "the", "of", "and", "in", "to", "for", "a", "an", "is", "are", "on", "by",
    "with", "as", "at", "from", "or", "this", "that", "be", "it", "was", "were",
}

STOPWORDS = STOPWORDS_ID | STOPWORDS_EN


def get_stopwords() -> set[str]:
    return STOPWORDS.copy()
