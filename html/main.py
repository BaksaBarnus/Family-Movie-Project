import http.server
import json
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from urllib.parse import urlparse

# Backend

# DB beállítások
PORT = 8000
PG_HOST = "127.0.0.1"
PG_PORT = 5432 
PG_DB = "family_movies"
PG_USER = "admin"
PG_PASS = "secretpassword"


# DB csatlakozási függvény
def get_pg_connection():
    return psycopg2.connect(
        host=PG_HOST,
        port=PG_PORT,
        dbname=PG_DB,
        user=PG_USER,
        password=PG_PASS
    )



# Itt származtatjuk le     VVV ebből az osztályból a szervert
class MovieBackendHandler(http.server.SimpleHTTPRequestHandler):

    # HTTP GET metódus
    def do_GET(self): #self maga a get kérés objektuma
        parsed_path = urlparse(self.path).path

        # REST API VÉGPONT: /api/movies
        # Ha a kérés ez, akkor lekéri az adatbázisból
        if parsed_path == "/api/movies":
            try:
                conn = get_pg_connection()
                cursor = conn.cursor(cursor_factory=RealDictCursor) #Python dictionarry
                cursor.execute("SELECT id, clean_title, year FROM movies ORDER BY clean_title ASC;") #SQL Lekérdezés
                movies = cursor.fetchall() #Lekérdezés adatai
                cursor.close()
                conn.close()
                #Kapcsolat bezárása

                # Válasz küldés JSON-ben
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8") #Header, JSON formátum
                self.send_header("Access-Control-Allow-Origin", "*") #CORS engedélyek
                self.end_headers()
                self.wfile.write(json.dumps(movies, ensure_ascii=False).encode("utf-8")) #Legyártja a JSON-t, ékezeteket átengedi

            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
            return

        # HA nem api kérés van, megjeleníti a főoldal
        if parsed_path == "/":
            if os.path.exists("html/index.html"):
                self.path = "/html/index.html"
            elif os.path.exists("index.html"):
                self.path = "/index.html"
        elif not os.path.exists("." + parsed_path) and os.path.exists("html" + parsed_path):
            self.path = "/html" + parsed_path

        return super().do_GET()


# Indítás

if __name__ == "__main__":
    print(f"🚀 A Python Backend fut a http://localhost:{PORT} címen!")
    print("💡 Nyisd meg a böngészőben: http://localhost:8000")

    server = http.server.HTTPServer(("0.0.0.0", PORT), MovieBackendHandler) #Létrehozzuk a szervert
    try:
        server.serve_forever() #Ez szolgálja ki a kéréseket egy végtelen ciklusban
    except KeyboardInterrupt:
        print("\n🛑 Szerver leállítva.")