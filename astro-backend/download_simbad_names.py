import gzip
import sqlite3
import requests
import os

DATA_URL = "http://cdsarc.cds.unistra.fr/ftp/VII/118/ident.dat.gz"
DB_PATH = "astro_names.db"

def download_and_extract():
    print("Downloading identifiers...")
    r = requests.get(DATA_URL, stream=True)
    if r.status_code != 200:
        print(f"Failed to download file: HTTP {r.status_code}")
        print(r.text[:500])
        raise Exception("Download failed")
    with open("ident.dat.gz", "wb") as f:
        for chunk in r.iter_content(chunk_size=8192):
            f.write(chunk)
    print("Downloaded ident.dat.gz, size:", os.path.getsize("ident.dat.gz"), "bytes")
    
    print("Extracting...")
    with gzip.open("ident.dat.gz", "rb") as f_in, open("ident.dat", "wb") as f_out:
        f_out.write(f_in.read())
    print("Extracted ident.dat, size:", os.path.getsize("ident.dat"), "bytes")
    print("Done.")

def create_db():
    print("Creating database...")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DROP TABLE IF EXISTS names")
    c.execute("""
        CREATE TABLE names (
            oid INTEGER,
            name TEXT
        )
    """)
    conn.commit()
    conn.close()
    print("Database created.")

def populate_db():
    print("Populating database...")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    with open("ident.dat", "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            oid = int(line[:9].strip())
            name = line[9:].strip()
            c.execute("INSERT INTO names (oid, name) VALUES (?, ?)", (oid, name))
    conn.commit()
    conn.close()
    print("Database populated.")

if __name__ == "__main__":
    if not os.path.exists("ident.dat"):
        download_and_extract()
    create_db()
    populate_db()
    print("All done.")