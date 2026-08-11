import http.server
import json
import os
import re
import shutil
import sqlite3
from urllib.parse import urlparse, parse_qs

#Settings
PORT = 8000
APP_DB = 'app.db'
SMB_DB_PATH = 'Y:/.minidlna/files.db'
TEMP_DB_PATH = 'temp_files.db'

#Database
def init_db():
    conn =sqlite3.connect(APP_DB)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS movies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            minidlna_id INTEGER UNIQUE,
            clean_title TEXT NOT NULL,
            year INTEGER,
            raw_filename TEXT,
            path TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS whislist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT not NULL,
            priority INTEGER DEFAULT 2
        )
        ''')
    conn.commit()
    conn.close()

def parse_filename(filename):
    # Remove file extension
    filename_without_extension = os.path.splitext(filename)[0]
    
    # Regex to match title and year
    match = re.search(r'^(.*?)[. _](19\d{2}|20\d{2})', filename_without_extension)
    if match:
        raw_title = match.group(1)
        year = int(match.group(2))
    else:
        raw_title = filename_without_extension
        year = None
    clean_title = re.sub(r'[._]', ' ', raw_title).strip()
    return clean_title, year

def safe_decode(val):
    """Biztonságosan dekódolja a bájtokat karakterlánccá (UTF-8, ISO-8859-2 vagy Latin-1)."""
    if val is None:
        return ""
    if isinstance(val, str):
        return val
    
    # Először UTF-8-cal próbálkozunk
    try:
        return val.decode('utf-8')
    except UnicodeDecodeError:
        try:
            # Ha nem UTF-8, megpróbáljuk a magyar/közép-európai kódolást
            return val.decode('iso-8859-2')
        except UnicodeDecodeError:
            # Vészhelyzeti fallback: kicseréli az ismeretlen karaktereket
            return val.decode('latin-1', errors='replace')


def sync_from_smb():
    if not os.path.exists(SMB_DB_PATH):
        raise FileNotFoundError(f"SMB nem elérhető {SMB_DB_PATH}")

    shutil.copy(SMB_DB_PATH, TEMP_DB_PATH)

    src_conn = sqlite3.connect(TEMP_DB_PATH)
    # 💡 KULCSLÉPÉS: Bájtként kérjük le a szövegeket, így a Python nem dob hibát az ékezeteknél!
    src_conn.text_factory = bytes
    src_cursor = src_conn.cursor()

    src_cursor.execute("""
        SELECT ID, TITLE, PATH 
        FROM DETAILS 
        WHERE PATH LIKE '%.mp4' OR PATH LIKE '%.mkv' OR PATH LIKE '%.avi'
           OR TITLE LIKE '%.mp4' OR TITLE LIKE '%.mkv' OR TITLE LIKE '%.avi'
    """)
    rows = src_cursor.fetchall()
    src_conn.close()

    dest_conn = sqlite3.connect(APP_DB)
    dest_cursor = dest_conn.cursor()
    count = 0

    for mini_id, db_title_bytes, path_bytes in rows:
        # Dekódoljuk a nyers bájtokat biztonságosan
        db_title = safe_decode(db_title_bytes)
        path = safe_decode(path_bytes)

        raw_filename = os.path.basename(path) if path else db_title
        clean_title, year = parse_filename(raw_filename)

        try:
            dest_cursor.execute("""
                INSERT INTO movies (minidlna_id, clean_title, year, raw_filename, path)
                VALUES (?, ?, ?, ?, ?)
            """, (mini_id, clean_title, year, raw_filename, path))
            count += 1
        except sqlite3.IntegrityError:
            # Duplikátumok kihagyása
            continue

    dest_conn.commit()
    dest_conn.close()

    if os.path.exists(TEMP_DB_PATH):
        os.remove(TEMP_DB_PATH)

    return count

if __name__ == "__main__":
    print("Inicializálás...")
    init_db()
    print("Inicializálás befejezve.")

    try:
        added_count = sync_from_smb()
        print(f"Szinkronizálás befejezve. {added_count} új film hozzáadva.")

        conn = sqlite3.connect(APP_DB)
        cursor = conn.cursor()
        cursor.execute("SELECT clean_title, year, raw_filename, path FROM movies LIMIT 20")
        sample = cursor.fetchall()

        print("Minta a szinkronizált filmekből:")
        for item in sample:
            print(f"Title: {item[0]}, Year: {item[1]}, Filename: {item[2]}, Path: {item[3]}")
        conn.close()

    except Exception as e:
        print(f"Hiba történt a szinkronizálás során: {e}")