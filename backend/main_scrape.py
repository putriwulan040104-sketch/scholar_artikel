from src.scraper.scholar_scraper import scrape_and_save_to_supabase

DEFAULT_TARGET = 50
def input_target():
    raw = input(f"Masukkan target artikel [{DEFAULT_TARGET}]: ").strip()
    if not raw:
        return DEFAULT_TARGET

    while True:
        try:
            target = int(raw)
            if target > 0:
                return target
        except ValueError:
            pass
        raw = input("Target harus angka lebih dari 0, coba lagi: ").strip()
def main():
    keyword = input("Masukkan keyword pencarian: ").strip()
    category = input("Masukkan kategori database: ").strip()
    target = input_target()

    if not keyword or not category:
        raise SystemExit("Keyword dan kategori database tidak boleh kosong.")

    print(
        "\nKonfigurasi scraping"
        f"\n- Keyword pencarian : {keyword}"
        f"\n- Kategori database : {category}"
        f"\n- Target artikel    : {target}\n"
    )
    scrape_and_save_to_supabase(keyword, category=category, max_results=target)

if __name__ == "__main__":
    main()
