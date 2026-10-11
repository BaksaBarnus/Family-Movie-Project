import os
import time
import subprocess
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# A figyelendő fájl és annak mappája
DB_PATH = "/mnt/sda1/.minidlna/files.db"
WATCH_DIR = os.path.dirname(DB_PATH)

class DatabaseHandler(FileSystemEventHandler):
    def __init__(self):
        self.last_sync = 0

    def on_modified(self, event):
        # 1. Csak akkor foglalkozunk vele, ha PONTOSAN a files.db módosult
        if event.src_path == DB_PATH:
            now = time.time()
            
            # 2. 10 másodperces "lehűlés", hogy az SQLite temp-fájl műveletei 
            # ne indítsák el 10-szer a szinkronizációt
            if now - self.last_sync > 10:
                print(f"🔄 Adatbázis változás észlelve! ({event.event_type}: {event.src_path})")
                
                # 3. Várunk 2 extra másodpercet, hogy a miniDLNA 
                # biztosan elengedje a fájl zárolását (lock)
                time.sleep(2)
                
                subprocess.run(["python", "sync_db.py"])
                
                # Frissítjük az utolsó szinkronizálás idejét
                self.last_sync = time.time()

if __name__ == "__main__":
    # Ha a mappa esetleg nem létezik (pl. első indítás), ne omoljon össze
    if not os.path.exists(WATCH_DIR):
        print(f"⚠️ A {WATCH_DIR} mappa nem létezik! Kérlek ellenőrizd az útvonalat.")
    else:
        print(f"👀 Automatikus adatbázis-figyelő elindítva: {DB_PATH}")
        event_handler = DatabaseHandler()
        observer = Observer()
        
        # Elég csak a .minidlna mappát figyelni, a recursive=False sokkal erőforráskímélőbb!
        observer.schedule(event_handler, WATCH_DIR, recursive=False)
        observer.start()

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
        observer.join()