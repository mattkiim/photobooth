import time
import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

WATCH_FOLDER = r"frame_designs/"

def upload_to_drive(path):
    # TODO: Implement with Google Drive / Dropbox / etc. API
    print(f"Uploading {path} to shared drive...")
    # e.g. drive_service.files().create(...)

class PhotoHandler(FileSystemEventHandler):
    def on_created(self, event):
        if not event.is_directory:
            if event.src_path.lower().endswith((".jpg", ".jpeg", ".png")):
                upload_to_drive(event.src_path)

if __name__ == "__main__":
    event_handler = PhotoHandler()
    observer = Observer()
    observer.schedule(event_handler, WATCH_FOLDER, recursive=False)
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
