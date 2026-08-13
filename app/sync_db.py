import os
import re
import shutil
import sqlite3
import urllib.request
import urllib.parse
import json

# Api és DB érzékeny adatok
from config import TMDB_API_KEY, PG_PASS, MINIDLNA_DB_PATH
from init_db import get_pg_connection, init_postgres_db

# Elérési utak
SMB_DB_PATH = MINIDLNA_DB_PATH
TEMP_DB_PATH = 'temp_files.db'

# További paraméterek
MIN_FILE_SIZE = 700 * 1024 * 1024
VALID_EXTENSIONS = ('.mkv', '.avi', '.mp4', '.mov', '.wmv', '.m4v')
ROOT_FOLDERS = ['Filmek', 'movies', 'actual', 'kozos', 'sajat', 'sda1', 'media']
TMDB_GENRES = {
    28: "Akció", 12: "Kaland", 16: "Animációs", 35: "Vígjáték", 80: "Bűnügyi",
    99: "Dokumentum", 18: "Dráma", 10751: "Családi", 14: "Fantasztikus",
    36: "Történelmi", 27: "Horror", 10402: "Zenei", 9648: "Rejtély",
    10749: "Romantikus", 878: "Sci-Fi", 10770: "TV film", 53: "Thriller",
    10752: "Háborús", 37: "Western", 10759: "Akció és Kaland",
    10762: "Gyerekeknek", 10765: "Sci-Fi és Fantasztikus"
}


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
            params[year_param] = year 

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

                    # Hivatalos cím, Eredeti cím és Műfajok kinyerése
                    title_key = "name" if is_tv_show else "title"
                    orig_title_key = "original_name" if is_tv_show else "original_title"

                    tmdb_title = first_match.get(title_key)
                    original_title = first_match.get(orig_title_key)

                    genre_ids = first_match.get("genre_ids", [])
                    genre_names = [TMDB_GENRES.get(gid) for gid in genre_ids if gid in TMDB_GENRES]

                    genres_str = ", ".join(genre_names) if genre_names else None

                    return {
                        "poster_path": first_match.get("poster_path"),
                        "overview": first_match.get("overview"),
                        "rating": first_match.get("vote_average"),
                        "tmdb_year": tmdb_year,
                        "tmdb_title": tmdb_title,
                        "original_title": original_title,
                        "genres": genres_str
                    }
        except Exception as e:
            print(f"⚠️ TMDB hiba ({title}, lang={lang}): {e}")

    return {
        "poster_path": None,
        "overview": None,
        "rating": None,
        "tmdb_year": None,
        "tmdb_title": None, 
        "original_title": None,
        "genres": None
    }


#Elemzi az elérési utat, kitisztítja a címet, kinyeri az évszámot és felismeri a sorozatokat.
def parse_parent_folder(path):
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
        pg_cursor.execute("""
            INSERT INTO movies (minidlna_id, clean_title, tmdb_title, original_title, genres, year, raw_filename, path, poster_path, overview, rating)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (minidlna_id) DO UPDATE SET
                clean_title = EXCLUDED.clean_title,
                tmdb_title = COALESCE(EXCLUDED.tmdb_title, movies.tmdb_title),
                original_title = COALESCE(EXCLUDED.original_title, movies.original_title),
                genres = COALESCE(EXCLUDED.genres, movies.genres),
                year = EXCLUDED.year,
                raw_filename = EXCLUDED.raw_filename,
                path = EXCLUDED.path,
                poster_path = COALESCE(EXCLUDED.poster_path, movies.poster_path),
                overview = COALESCE(EXCLUDED.overview, movies.overview),
                rating = COALESCE(EXCLUDED.rating, movies.rating);
        """, (
            mini_id, 
            clean_title,
            tmdb_info.get("tmdb_title"),
            tmdb_info.get("original_title"),
            tmdb_info.get("genres"),
            year, 
            raw_filename, 
            path, 
            tmdb_info.get("poster_path"), 
            tmdb_info.get("overview"), 
            tmdb_info.get("rating")
        ))
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
    
    print(f"🔄 Szinkronizálás indítása az SMB meghajtóról: {SMB_DB_PATH} ...")
    try:
        added_count = sync_smb_to_postgres()
        print(f"🎉 Sikeres szinkronizálás! {added_count} film feldolgozva a PostgreSQL-ben.")
    except Exception as e:
        print(f"❌ Hiba történt: {e}")