"""
Utility logging untuk proses scraping.
Semua fungsi di sini HANYA mencetak (print) baris log yang sudah diformat
oleh pemanggil — isi/teks log tidak diubah, hanya dipindahkan ke sini
supaya scholar_scraper.py lebih bersih dan tidak dipenuhi print() manual.
"""


def log_page(*lines):
    """Log header status halaman scraping (mis. blok '📄 Halaman X ...')."""
    for line in lines:
        print(line)


def log_browser(*lines):
    """Log state browser: current URL, title, context, dsb."""
    for line in lines:
        print(line)


def log_retry(*lines):
    """Log percobaan retry (driver.get, reload halaman kosong, restart session, dsb)."""
    for line in lines:
        print(line)


def log_warning(*lines):
    """Log peringatan non-fatal (⚠), mis. timeout, redirect tak terduga, gagal sementara."""
    for line in lines:
        print(line)


def log_skip(*lines):
    """Log artikel yang di-skip karena tidak memenuhi kriteria validasi."""
    for line in lines:
        print(line)


def log_success(*lines):
    """Log artikel valid / berhasil masuk temporary dataset."""
    for line in lines:
        print(line)


def log_finish(*lines):
    """Log ringkasan akhir proses scraping (target tercapai/tidak, dihentikan, dsb)."""
    for line in lines:
        print(line)


def log_error(*lines):
    """Log kegagalan fatal yang menghentikan proses scraping (❌)."""
    for line in lines:
        print(line)