import sys
from src.scraper.scholar_scraper import scrape_and_save_to_supabase

if __name__ == "__main__":
    # Dua cara pakai:
    #   python main_scrape.py                    → prompt interaktif
    #   python main_scrape.py "machine learning" → argumen CLI
    if len(sys.argv) > 1:
        keyword = " ".join(sys.argv[1:]).strip()
        print(f"🔑 Keyword: {keyword}")
    else:
        keyword = input("Masukkan keyword: ").strip()

    if not keyword:
        print("❌ Keyword tidak boleh kosong.")
        sys.exit(1)

    scrape_and_save_to_supabase(keyword, category=keyword, max_results=50)