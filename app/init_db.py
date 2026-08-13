import psycopg2
from config import PG_HOST, PG_PORT, PG_DB, PG_USER, PG_PASS

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

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS movies(
            id SERIAL PRIMARY KEY,
            minidlna_id INTEGER UNIQUE,
            clean_title VARCHAR(255) NOT NULL,
            tmdb_title VARCHAR(255),
            original_title VARCHAR(255),
            genres VARCHAR(255),
            year INTEGER,
            raw_filename TEXT,
            path TEXT,
            poster_path TEXT,
            overview TEXT,
            rating NUMERIC(3, 1)
        );
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS wishlist(
            id SERIAL PRIMARY KEY,
            title VARCHAR(255),
            priority INTEGER DEFAULT 2,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            ''')
    
    conn.commit()
    cursor.close()
    conn.close()
    print("✅ PostgreSQL táblák ellenőrizve/létrehozva!")

if __name__ == '__main__':
    print("🚀 PostgreSQL Adatbázis inicializálása...")
    init_postgres_db()
        