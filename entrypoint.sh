#!/bin/sh

set -e

echo "🚀 Konténer indítása..."

cd /app/app

python init_db.py
python sync_db.py || echo "Kezdő szinkronizáció figyelmeztetéssel fejeződött be."
python watcher.py &

echo "✨ Webalkalmazás indítása..."
exec python main.py