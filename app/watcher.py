import time
import subprocess
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

WATCH_PATH = "/mnt/sda1"

class MovieFolderHandler(FileSystemEventHandler):
    def __init__(self):
        self.last_sync = 0

    def on_any_event(self, event):
        if event.is_directory or event.src_path.endswith(('.mkv', '.mp4', '.avi')):
            now = time.time()
            if now - self.last_sync > 10:
                print(f"🔄 Fájlrendszer változás észlelve ({event.event_type}: {event.src_path})")
                subprocess.run(["python", "sync_db.py"])
                self.last_sync = now

if __name__ == "__main__":
    print(f"👀 Automatikus könyvtárfigyelő elindítva a következő útvonalon: {WATCH_PATH}")
    event_handler =MovieFolderHandler()
    observer = Observer()
    observer.schedule(event_handler, WATCH_PATH, recursive=True)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()