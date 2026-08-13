import http.server
import json
import os
from psycopg2.extras import RealDictCursor
from urllib.parse import urlparse, parse_qs

from init_db import get_pg_connection, init_postgres_db

# Backend

PORT = 8000
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(CURRENT_DIR)
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")

# Itt származtatjuk le     VVV ebből az osztályból a szervert
class MovieBackendHandler(http.server.SimpleHTTPRequestHandler):

    def translate_path(self, path):
        """Ez a Python hivatalos metódusa a kért URL és a merevlemez-útvonal összekötésére."""
        parsed_path = path.split("?")[0]

        # Gyökér kérés esetén az index.html-re mutatunk
        if parsed_path == "/":
            parsed_path = "/index.html"

        # Eltávolítjuk a kezdő perjelet, és hozzáfűzzük a FRONTEND_DIR-hez
        clean_path = parsed_path.lstrip("/")
        return os.path.join(FRONTEND_DIR, clean_path)

    def send_json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    # HTTP GET metódus
    def do_GET(self): #self maga a get kérés objektuma
        parsed_path = urlparse(self.path).path

        # REST API VÉGPONT: /api/movies
        # Ha a kérés ez, akkor lekéri az adatbázisból
        if parsed_path == '/api/movies':
            try:
                conn = get_pg_connection()
                cursor = conn.cursor(cursor_factory=RealDictCursor) #Python dictionarry
                cursor.execute('''
                    SELECT DISTINCT ON (COALESCE(tmdb_title, clean_title)) 
                    id, clean_title, tmdb_title, original_title, genres, year, poster_path, overview, rating::FLOAT, path 
                    FROM movies 
                    ORDER BY COALESCE(tmdb_title, clean_title) ASC, id ASC;
                ''') 
                movies = cursor.fetchall() #Lekérdezés adatai
                cursor.close()
                conn.close()

                # Válasz küldés JSON-ben
                self.send_json(movies)
            except Exception as e:
                self.send_json({'error': str(e)}, 500)
            return

        if parsed_path == '/api/wishlist':
            try:
                conn = get_pg_connection()
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                cursor.execute("SELECT id, title, created_at::TEXT FROM wishlist ORDER BY id DESC;")
                items = cursor.fetchall()
                cursor.close()
                conn.close()

                self.send_json(items)
            except Exception as e:
                self.send_json({'error': str(e)}, 500)
            return

        # HA nem api kérés van, statikus fájlokat szolgálunk ki
        if parsed_path == '/':
             self.path = '../frontend/index.html'
        elif not parsed_path.startswith('/frontend'):
            relative_path = '../frontend' + parsed_path
            if os.path.exists(relative_path):
                self.path = relative_path

        return super().do_GET()
    
    # POST metódus
    def do_POST(self):
        parsed_path = urlparse(self.path).path

        if parsed_path == "/api/wishlist":
            try:
                content_length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(content_length).decode("utf-8")
                data = json.loads(body)
                title = data.get("title", "").strip()

                if not title:
                    self.send_json({"error": "Hiányzó cím!"}, 400)
                    return

                conn = get_pg_connection()
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                cursor.execute(
                    "INSERT INTO wishlist (title) VALUES (%s) RETURNING id, title;",
                    (title,),
                )
                new_item = cursor.fetchone()
                conn.commit()
                cursor.close()
                conn.close()

                self.send_json(new_item, 201)
            except Exception as e:
                self.send_json({"error": str(e)}, 500)
            return

    # DELETE metódus
    def do_DELETE(self):
        parsed_url = urlparse(self.path)
        parsed_path = parsed_url.path

        if parsed_path == "/api/wishlist":
            try:
                query_params = parse_qs(parsed_url.query)
                item_id = query_params.get("id", [None])[0]

                if not item_id:
                    self.send_json({"error": "Hiányzó ID!"}, 400)
                    return

                conn = get_pg_connection()
                cursor = conn.cursor()
                cursor.execute(
                    "DELETE FROM wishlist WHERE id = %s;", (item_id,)
                )
                conn.commit()
                cursor.close()
                conn.close()

                self.send_json({"success": True})
            except Exception as e:
                self.send_json({"error": str(e)}, 500)
            return

# Indítás

if __name__ == '__main__':
    print(f'🚀 A Python Backend fut a http://localhost:{PORT} címen!')
    print('💡 Nyisd meg a böngészőben: http://localhost:8000')

    server = http.server.HTTPServer(('0.0.0.0', PORT), MovieBackendHandler) # Létrehozzuk a szervert
    try:
        server.serve_forever() #Ez szolgálja ki a kéréseket egy végtelen ciklusban

    except KeyboardInterrupt:
        print('\n🛑 Szerver leállítva.')