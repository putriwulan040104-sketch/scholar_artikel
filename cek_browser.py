"""
Script untuk cek versi Chrome dan ChromeDriver
Gunakan ini untuk memastikan kompatibilitas
"""

import os
import sys
import subprocess

print("="*60)
print("CEK VERSI CHROME & CHROMEDRIVER")
print("="*60)

# 1. Cek instalasi Chrome
print("\n[1] Mencari instalasi Chrome...")
chrome_paths = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
]

chrome_found = None
for path in chrome_paths:
    if os.path.exists(path):
        chrome_found = path
        print(f"✓ Chrome ditemukan: {path}")
        break

if not chrome_found:
    print("✗ Chrome tidak ditemukan di lokasi standar")
    print("  Pastikan Chrome sudah terinstall!")
else:
    # Cek versi Chrome
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Google\Chrome\BLBeacon")
        version, _ = winreg.QueryValueEx(key, "version")
        print(f"  Versi Chrome: {version}")
        
        # Cek apakah 32-bit atau 64-bit
        if "(x86)" in chrome_found:
            print("  ⚠ WARNING: Ini Chrome 32-bit!")
            print("  Disarankan install Chrome 64-bit untuk stabilitas lebih baik")
        else:
            print("  ✓ Chrome 64-bit")
    except:
        print("  (Tidak bisa deteksi versi otomatis)")

# 2. Cek ChromeDriver
print("\n[2] Mencari ChromeDriver...")
try:
    from webdriver_manager.chrome import ChromeDriverManager
    
    print("Mengecek/download ChromeDriver via webdriver-manager...")
    driver_path = ChromeDriverManager().install()
    print(f"✓ ChromeDriver ditemukan: {driver_path}")
    
    # Cek versi ChromeDriver
    try:
        result = subprocess.run([driver_path, "--version"], capture_output=True, text=True)
        version_output = result.stdout.strip()
        print(f"  Versi: {version_output}")
    except:
        print("  (Tidak bisa deteksi versi)")
        
except Exception as e:
    print(f"✗ Error: {str(e)}")

# 3. Cek Python packages
print("\n[3] Cek Python packages...")
packages = ['selenium', 'webdriver-manager']
for pkg in packages:
    try:
        if pkg == 'webdriver-manager':
            import webdriver_manager
            version = webdriver_manager.__version__
        else:
            import selenium
            version = selenium.__version__
        print(f"✓ {pkg}: {version}")
    except ImportError:
        print(f"✗ {pkg}: TIDAK TERINSTALL!")

# 4. Test minimal Chrome startup
print("\n[4] Test Chrome startup...")
print("Mencoba membuat driver Chrome sederhana...")

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from webdriver_manager.chrome import ChromeDriverManager
    
    options = Options()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    # JANGAN gunakan headless untuk test ini
    
    service = Service(ChromeDriverManager().install())
    
    print("  Membuat driver (Chrome window akan muncul)...")
    driver = webdriver.Chrome(service=service, options=options)
    
    print("  ✓ Chrome berhasil start!")
    print("  Mencoba buka Google...")
    
    driver.get("https://www.google.com")
    print(f"  ✓ Berhasil! Title: {driver.title}")
    
    driver.quit()
    print("  ✓ Chrome ditutup dengan baik")
    
    print("\n" + "="*60)
    print("SEMUA CEK PASSED! ✓")
    print("="*60)
    print("\nChrome + Selenium Anda berfungsi dengan baik!")
    print("Silakan jalankan: python scrape_article_debug.py")
    
except Exception as e:
    print(f"\n✗ GAGAL!")
    print(f"Error: {str(e)}\n")
    
    print("="*60)
    print("DIAGNOSIS & SOLUSI")
    print("="*60)
    print("\nKemungkinan masalah:")
    print("1. Chrome versi lama atau corrupt")
    print("   → Update Chrome ke versi terbaru")
    print("   → Download: https://www.google.com/chrome/")
    print()
    print("2. ChromeDriver tidak cocok dengan Chrome")
    print("   → Hapus cache: C:\\Users\\YourUsername\\.wdm\\")
    print("   → Jalankan script ini lagi")
    print()
    print("3. Antivirus blocking ChromeDriver")
    print("   → Tambahkan exception untuk Python dan ChromeDriver")
    print()
    print("4. Permission issue")
    print("   → Jalankan PowerShell sebagai Administrator")
    print()
    print("5. Gunakan alternatif browser (Firefox)")
    print("   → pip install geckodriver")
    
    import traceback
    print("\nFull traceback:")
    traceback.print_exc()

print("\n" + "="*60)