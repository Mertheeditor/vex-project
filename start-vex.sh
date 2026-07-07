#!/bin/bash

set -e

VEX_ROOT="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$VEX_ROOT/vex-backend"
APP_DIR="$VEX_ROOT/vex-app"

BACKEND_PORT="8000"
TAURI_PORT="1420"
VITE_PORT="5173"

echo "========================================"
echo "Vex başlatılıyor..."
echo "Kök klasör: $VEX_ROOT"
echo "Backend: $BACKEND_DIR"
echo "Frontend: $APP_DIR"
echo "========================================"

if [ ! -d "$BACKEND_DIR" ]; then
  echo "Hata: Backend klasörü bulunamadı: $BACKEND_DIR"
  exit 1
fi

if [ ! -d "$APP_DIR" ]; then
  echo "Hata: Frontend klasörü bulunamadı: $APP_DIR"
  exit 1
fi

if [ ! -f "$BACKEND_DIR/main.py" ]; then
  echo "Hata: Backend main.py bulunamadı."
  exit 1
fi

if [ ! -f "$APP_DIR/package.json" ]; then
  echo "Hata: Frontend package.json bulunamadı."
  exit 1
fi

echo ""
echo "==> Eski processler kapatılıyor..."

lsof -ti :$BACKEND_PORT | xargs kill -9 2>/dev/null || true
lsof -ti :$TAURI_PORT | xargs kill -9 2>/dev/null || true
lsof -ti :$VITE_PORT | xargs kill -9 2>/dev/null || true

echo ""
echo "==> Backend sanal ortam kontrol ediliyor..."

cd "$BACKEND_DIR"

if [ ! -d ".venv" ]; then
  echo ".venv bulunamadı. Yeni sanal ortam oluşturuluyor..."
  python3 -m venv .venv
fi

source .venv/bin/activate

if [ -f "requirements.txt" ]; then
  echo "Backend paketleri kontrol/kurulum..."
  python -m pip install --upgrade pip >/dev/null
  pip install -r requirements.txt
fi

echo ""
echo "==> Frontend node_modules kontrol ediliyor..."

cd "$APP_DIR"

if [ ! -d "node_modules" ]; then
  echo "node_modules bulunamadı. npm install çalıştırılıyor..."
  npm install
fi

echo ""
echo "==> Backend ayrı Terminal penceresinde başlatılıyor..."

osascript -e "tell application \"Terminal\" to do script \"cd '$BACKEND_DIR' && source .venv/bin/activate && uvicorn main:app --reload --host 127.0.0.1 --port $BACKEND_PORT\""

echo ""
echo "==> Backend hazır olması bekleniyor..."

for i in {1..30}; do
  if curl -s "http://127.0.0.1:$BACKEND_PORT/" >/dev/null 2>&1; then
    echo "Backend hazır: http://127.0.0.1:$BACKEND_PORT"
    break
  fi

  if [ "$i" -eq 30 ]; then
    echo "Backend zamanında hazır olmadı. Terminal penceresindeki backend hatasını kontrol et."
    exit 1
  fi

  sleep 1
done

echo ""
echo "==> Vex Tauri uygulaması başlatılıyor..."
cd "$APP_DIR"
npm run tauri dev
