import os
import re
import shutil
import sqlite3
import psycopg2

#Elérési utak
SMB_DB_PATH = 'Z:/.minidlna/files.db'
TEMP_DB_PATH = 'temp_files.db'

#PostgreSQL kapcsolat
PG_HOST = "localhost"
PG_PORT = 5432
PG_DB = "family_movies"
PG_USER = "admin"
PG_PASS = "secretpassword"


#PostgreSQL kapcsolat létrehozás
def get_pg_connection():
    return psycopg2.connect(
        host=PG_HOST,
        port=PG_PORT,
        dbname=PG_DB,
        user=PG_USER,
        password=PG_PASS
    )

def init_postgres_db():
    conn = get_pg_connection()
    cursor = conn.cursor()
    
    #Movies tábla
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS movies (
            id SERIAL PRIMARY KEY,
            minidlna_id INTEGER UNIQUE,
            clean_title VARCHAR(255) NOT NULL,
            year INTEGER,
            raw_filename TEXT,
            path TEXT
        );
    ''')
    
    #Wishlist tábla
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS wishlist (
            id SERIAL PRIMARY KEY,
            title VARCHAR(255) NOT NULL,
            priority INTEGER DEFAULT 2,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    ''')
    
    conn.commit()
    cursor.close()
    conn.close()
    print("✅ PostgreSQL táblák ellenőrizve/létrehozva!")


# --- HELPER FUNKCIÓK (A régiek) ---
def safe_decode(val):
    if val is None:
        return ''
    if isinstance(val, str):
        return val
    try:
        return val.decode('utf-8')
    except UnicodeDecodeError:
        try:
            return val.decode('iso-8859-2')
        except UnicodeDecodeError:
            return val.decode('latin-1', errors='replace')

def parse_filename(filename):
    # Kiterjesztés eltávolítása (.mkv, .mp4, stb.)
    name_without_ext = os.path.splitext(filename)[0]

    #Release csoportok / előtagok eltávolítása a fájlnév elejéről
    #Konkrét ismert szavak (fulcrum, pirosasz, hun, sub, stb.)
    #Bármilyen 2-4 betűs kód a fájl legelején, amit kötőjel/pont/alsóvonal követ (pl. zhr-, hrt-, gl-)
    cleaned_name = re.sub(
        r'^(fulcrum|pirosasz|hun|sub|evo|rarbg|[a-z0-9]{2,3})[._-]',
        '',
        name_without_ext,
        flags=re.IGNORECASE,
    )

    # 2. Évszám keresése (19xx vagy 20xx)
    match = re.search(r'^(.*?)[. _-](19\d{2}|20\d{2})', cleaned_name)

    if match:
        raw_title = match.group(1)
        year = int(match.group(2))
    else:
        # 3. HA NINCS ÉVSZÁM: Elvágjuk az első minőségi/tech megnevezésnél!
        raw_title = re.split(
            r'[. _-](720p|1080p|2160p|4k|bluray|bdrip|webrip|web-dl|dvdrip|x264|x265|h264|h265)',
            cleaned_name,
            flags=re.IGNORECASE,
        )[0]
        year = None

    # 4. Kötőjelek, pontok és alsóvonalak cseréje szóközre
    clean_title = re.sub(r'[._-]', ' ', raw_title).strip()

    # 5. Ha a cím elején mégis ott maradt egy beragadt rövid tag, letakarítjuk
    clean_title = re.sub(
        r'^(zhr|hrt|gl|fulcrum|pirosasz)\s+',
        '',
        clean_title,
        flags=re.IGNORECASE,
    )

    # 6. Szép nagy kezdőbetűs formátum (Title Case: "zhr-cars" -> "Cars")
    clean_title = clean_title.title()

    return clean_title, year

#SQLiteból PostgreSQL-be
def sync_smb_to_postgres():
    if not os.path.exists(SMB_DB_PATH):
        raise FileNotFoundError(f"SMB nem elérhető: {SMB_DB_PATH}")

    # 1. Beolvasás SQLite-ból (SMB-ről másolva)
    shutil.copy(SMB_DB_PATH, TEMP_DB_PATH)

    src_conn = sqlite3.connect(TEMP_DB_PATH)
    src_conn.text_factory = bytes
    src_cursor = src_conn.cursor()
    src_cursor.execute("""
        SELECT ID, TITLE, PATH 
        FROM DETAILS 
        WHERE ( 
            PATH LIKE '%.mp4' OR PATH LIKE '%.mkv' OR PATH LIKE '%.avi'
            OR TITLE LIKE '%.mp4' OR TITLE LIKE '%.mkv' OR TITLE LIKE '%.avi'
            ) AND SIZE >= 838860800
    """)
    rows = src_cursor.fetchall()
    src_conn.close()

    if os.path.exists(TEMP_DB_PATH):
        os.remove(TEMP_DB_PATH)

    # 2. Írás a PostgreSQL adatbázisba
    pg_conn = get_pg_connection()
    pg_cursor = pg_conn.cursor()

    pg_cursor.execute("SELECT COUNT(*) FROM movies;")
    existing_count = pg_cursor.fetchone()[0]

    if existing_count > 0:
        print(f"⚠️ A PostgreSQL adatbázis már tartalmaz {existing_count} rekordot. Régi adatok törlése...")
        pg_cursor.execute("DELETE FROM movies;")
        pg_cursor.execute("TRUNCATE TABLE movies RESTART IDENTITY;")
        print("🗑️ Régi adatok törölve a PostgreSQL adatbázisból.")
    


    count = 0

    for mini_id, db_title_bytes, path_bytes in rows:
        db_title = safe_decode(db_title_bytes)
        path = safe_decode(path_bytes)
        raw_filename = os.path.basename(path) if path else db_title
        clean_title, year = parse_filename(raw_filename)

        # Postgres UPSERT szintaxis: ON CONFLICT ... DO UPDATE
        # PostgreSQL-ben ? helyett %s az átadott elemek jele!
        pg_cursor.execute("""
            INSERT INTO movies (minidlna_id, clean_title, year, raw_filename, path)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (minidlna_id) DO UPDATE SET
                clean_title = EXCLUDED.clean_title,
                year = EXCLUDED.year,
                raw_filename = EXCLUDED.raw_filename,
                path = EXCLUDED.path;
        """, (mini_id, clean_title, year, raw_filename, path))
        count += 1

    pg_conn.commit()
    pg_cursor.close()
    pg_conn.close()

    return count


#MAIN
if __name__ == '__main__':
    print("🚀 PostgreSQL Adatbázis inicializálása...")
    init_postgres_db()
    
    print(f"🔄 Szinkronizálás indítása az SMB meghajtóról: {SMB_DB_PATH} ...")
    try:
        added_count = sync_smb_to_postgres()
        print(f"🎉 Sikeres szinkronizálás! {added_count} film feldolgozva a PostgreSQL-ben.")
    except Exception as e:
        print(f"❌ Hiba történt: {e}")