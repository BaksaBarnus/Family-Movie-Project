import os
import re
import shutil
import sqlite3
import psycopg2
import urllib.request
import urllib.parse
import json

# Api és DB érzékeny adatok
from config import TMDB_API_KEY, PG_PASS

# Elérési utak
SMB_DB_PATH = 'Z:/.minidlna/files.db'
TEMP_DB_PATH = 'temp_files.db'

# PostgreSQL kapcsolat
PG_HOST = "localhost"
PG_PORT = 5432
PG_DB = "family_movies"
PG_USER = "admin"

# További paraméterek
MIN_FILE_SIZE = 700 * 1024 * 1024
VALID_EXTENSIONS = ('.mkv', '.avi', '.mp4', '.mov', '.wmv', '.m4v')
ROOT_FOLDERS = ['Filmek', 'movies', 'actual', 'kozos', 'sajat', 'sda1', 'media']


# PostgreSQL kapcsolat létrehozás
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
    
    # Movies tábla
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS movies (
            id SERIAL PRIMARY KEY,
            minidlna_id INTEGER UNIQUE,
            clean_title VARCHAR(255) NOT NULL,
            year INTEGER,
            raw_filename TEXT,
            path TEXT,
            poster_path TEXT,
            overview TEXT,
            rating NUMERIC(3, 1)
        );
    ''')
    
    # Wishlist tábla
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

# Ékezetek
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

# Egyéb videóanyagok kiszűrése
def is_valid_movie_file(path, size):
    if not size or size < MIN_FILE_SIZE:
        return False
    if not path.lower().endswith(VALID_EXTENSIONS):
        return False
    return True

# Alapértelmezetten az év üres, ha nincsen, is_tv_show szintén False kezdőérték
def get_tmdb_data(title, year=None, is_tv_show=False):
    """TMDB API lekérdezése (hu-HU próbálkozás, en-US tartalékkal)."""
    endpoint = "tv" if is_tv_show else "movie"
    base_url = f"https://api.themoviedb.org/3/search/{endpoint}"

    for lang in ["hu-HU", "en-US"]:
        params = {"api_key": TMDB_API_KEY, "query": title, "language": lang}

        if year:
            year_param = (
                "first_air_date_year" if is_tv_show else "primary_release_year"
            )
            params[year_param] = year  # 🟢 JAVÍTVA: Dinamikus kulcsérték!

        url = f"{base_url}?{urllib.parse.urlencode(params)}"

        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": "Mozilla/5.0"}
            )
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode("utf-8"))

                if data.get("results") and len(data["results"]) > 0:
                    first_match = data["results"][0]

                    date_key = "first_air_date" if is_tv_show else "release_date"
                    release_date = first_match.get(date_key, "")

                    tmdb_year = None
                    if (
                        release_date
                        and len(release_date) >= 4
                        and release_date[:4].isdigit()
                    ):
                        tmdb_year = int(release_date[:4])

                    return {
                        "poster_path": first_match.get("poster_path"),
                        "overview": first_match.get("overview"),
                        "rating": first_match.get("vote_average"),
                        "tmdb_year": tmdb_year,
                    }
        except Exception as e:
            print(f"⚠️ TMDB hiba ({title}, lang={lang}): {e}")

    return {
        "poster_path": None,
        "overview": None,
        "rating": None,
        "tmdb_year": None,
    }


def parse_parent_folder(path):
    """Elemzi az elérési utat, kitisztítja a címet, kinyeri az évszámot és felismeri a sorozatokat."""
    raw_filename = os.path.basename(path)
    parent_folder = os.path.basename(os.path.dirname(path))

    # Ellenőrzés, hogy szülőmappa vagy fájlnév a keresett
    if parent_folder and parent_folder.lower() not in ROOT_FOLDERS:
        target_string = parent_folder
        is_from_folder = True
    else:
        target_string = raw_filename
        is_from_folder = False

    # Kiterjesztés 
    target_string = re.sub(
        r"\.(mkv|mp4|avi|mov|wmv|m4v)$", "", target_string, flags=re.IGNORECASE
    )

    # Sorozat ?
    combined_name = f"{parent_folder} {raw_filename}"
    is_tv_show = bool(
        re.search(
            r"\b(s\d{1,2}|season\s*\d+|e\d{1,2})\b",
            combined_name,
            flags=re.IGNORECASE,
        )
    )

    # Karakterek cseréje szóközre
    clean_name = re.sub(r"[\._\-]", " ", target_string)

    # Prefixek lecsapása 
    if not is_from_folder:
        clean_name = re.sub(
            r"^\s*(hdtv|pdtv|dvdrip|bluray|gl|hrt|fulcrum)\s+",
            "",
            clean_name,
            flags=re.IGNORECASE,
        )

    # Évad / epizód jelölések
    clean_name = re.sub(
        r"\b(s\d{1,2}(e\d{1,2})?|season\s*\d+|e\d{1,2})\b",
        "",
        clean_name,
        flags=re.IGNORECASE,
    )

    # Évszám keresése
    year_match = re.search(r"\b(19\d\d|20\d\d)\b", clean_name)
    year = int(year_match.group(1)) if year_match else None

    # Cím levágása az évszámnál vagy egyéb szavaknál
    if year_match:
        title = clean_name[: year_match.start()]
    else:
        title = re.split(
            r"\b(720p|1080p|2160p|bluray|bdrip|web|dvdrip|x264|x265|hun|hdtv)\b",
            clean_name,
            flags=re.IGNORECASE,
        )[0]

    # Sorszámok eltávolítása a cím elejéről
    title_without_num = re.sub(r"^\s*\d{1,3}\s*[\.\-]?\s+", "", title)
    if title_without_num.strip():
        title = title_without_num

    if not title.strip():
        title = clean_name

    clean_title = " ".join(title.split()).strip()

    return clean_title, year, is_tv_show


def sync_smb_to_postgres():
    # SQLite másolása és beolvasása
    shutil.copy(SMB_DB_PATH, TEMP_DB_PATH)

    src_conn = sqlite3.connect(TEMP_DB_PATH)
    src_conn.text_factory = bytes
    cursor = src_conn.cursor()

    cursor.execute("SELECT ID, PATH, SIZE FROM DETAILS WHERE PATH IS NOT NULL;")
    rows = cursor.fetchall()

    src_conn.close()

    if os.path.exists(TEMP_DB_PATH):
        os.remove(TEMP_DB_PATH)

    # PostgreSQL 
    pg_conn = get_pg_connection()
    pg_cursor = pg_conn.cursor()

    count = 0
    tmdb_cache = {}
    active_minidlna_ids = []

    for mini_id, path_bytes, size in rows:
        path = safe_decode(path_bytes)

        # Szűrés méret és kiterjesztés alapján
        if not is_valid_movie_file(path, size):
            continue

        # Cím kinyerése
        clean_title, year, is_tv_show = parse_parent_folder(path)

        if not clean_title:
            continue

        active_minidlna_ids.append(mini_id)

        cache_key = f"{clean_title}_{year}_{is_tv_show}"
        if cache_key in tmdb_cache:
            tmdb_info = tmdb_cache[cache_key]
        else:
            tmdb_info = get_tmdb_data(clean_title, year, is_tv_show=is_tv_show)
            tmdb_cache[cache_key] = tmdb_info

        if not year and tmdb_info.get("tmdb_year"):
            year = tmdb_info.get("tmdb_year")

        raw_filename = os.path.basename(path)

        # Upsert
        pg_cursor.execute(
            """
            INSERT INTO movies (minidlna_id, clean_title, year, raw_filename, path, poster_path, overview, rating)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (minidlna_id) DO UPDATE SET
                clean_title = EXCLUDED.clean_title,
                year = EXCLUDED.year,
                raw_filename = EXCLUDED.raw_filename,
                path = EXCLUDED.path,
                poster_path = COALESCE(EXCLUDED.poster_path, movies.poster_path),
                overview = COALESCE(EXCLUDED.overview, movies.overview),
                rating = COALESCE(EXCLUDED.rating, movies.rating);
        """,
            (
                mini_id,
                clean_title,
                year,
                raw_filename,
                path,
                tmdb_info.get("poster_path"),
                tmdb_info.get("overview"),
                tmdb_info.get("rating"),
            ),
        )
        count += 1

    # Törölt, megszűnt elemek
    if active_minidlna_ids:
        pg_cursor.execute("""
            DELETE FROM movies 
            WHERE minidlna_id NOT IN %s;
        """, (tuple(active_minidlna_ids),))
        
        deleted_count = pg_cursor.rowcount
        if deleted_count > 0:
            print(f"🧹 Takarítás: {deleted_count} db törölt/árva rekord eltávolítva a PostgreSQL-ből.")

    pg_conn.commit()
    pg_cursor.close()
    pg_conn.close()

    return count 

# MAIN
if __name__ == '__main__':
    print("🚀 PostgreSQL Adatbázis inicializálása...")
    init_postgres_db()
    
    print(f"🔄 Szinkronizálás indítása az SMB meghajtóról: {SMB_DB_PATH} ...")
    try:
        added_count = sync_smb_to_postgres()
        print(f"🎉 Sikeres szinkronizálás! {added_count} film feldolgozva a PostgreSQL-ben.")
    except Exception as e:
        print(f"❌ Hiba történt: {e}")