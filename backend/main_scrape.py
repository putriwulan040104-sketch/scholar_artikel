from src.scraper.scholar_scraper import scrape_and_save_to_supabase

if __name__ == "__main__":
    keyword = input("Masukkan kata kunci: ").strip()
    category = keyword

    scrape_and_save_to_supabase(keyword, category, max_results=50)