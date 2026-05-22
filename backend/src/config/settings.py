import os
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
TABLE_NAME = "scholar_articles"
PDF_DIR = "pdfs"
os.makedirs(PDF_DIR, exist_ok=True)
