#!/bin/bash

set -e

VEX_ROOT="$HOME/Vex"
BACKEND_DIR="$VEX_ROOT/vex-backend"
APP_DIR="$VEX_ROOT/vex-app"

echo "Vex başlatılıyor..."
echo "Backend klasörü: $BACKEND_DIR"
echo "Uygulama klasörü: $APP_DIR"

if [ ! -d "$BACKEND_DIR" ]; then
  echo "Hata: vex-backend klasörü bulunamadı."
  exit 1
fi

if [ ! -d "$APP_DIR" ]; then
  echo "Hata: vex-app klasörü bulunamadı."
  exit 1
fi

echo "Eski backend process varsa kapatılıyor..."
lsof -ti :8000 | xargs kill -9 2>/dev/null || true

echo "Eski Vite/Tauri port process varsa kapatılıyor..."
lsof -ti :1420 | xargs kill -9 2>/dev/null || true
lsof -ti :5173 | xargs kill -9 2>/dev/null || true

echo "Backend başlatılıyor..."
osascript -e "tell application \"Terminal\" to do script \"cd '$BACKEND_DIR' && source .venv/bin/activate && uvicorn main:app --reload\""

echo "Backend'in hazır olması bekleniyor..."
sleep 4

echo "Vex uygulaması başlatılıyor..."
cd "$APP_DIR"
npm run tauri dev
