# Vex Project Context

Vex, Mert'in kişisel yapay zeka iş arkadaşıdır.

## Mimari

- Frontend: `vex-app` — React + TypeScript + Vite/Tauri
- Backend: `vex-backend` — FastAPI
- Backend portu: `127.0.0.1:8000`

## Modüler Backend Kuralları

- `main.py` sadece app oluşturur ve router include eder.
- Ağır/opsiyonel importlar `main.py` içinde yapılmaz.
- Gemini, Whisper, sounddevice, mss ve pyautogui eksikse backend çökmez; sadece ilgili endpoint anlamlı hata döner.
- JSON storage korunur. Veritabanına geçiş sonraki aşamadır.

## Çalıştırma

```bash
cd /Users/mert/Vex/vex-backend
source .venv/bin/activate
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

## Test

```bash
curl -i http://127.0.0.1:8000/health
curl -i http://127.0.0.1:8000/computer/status
curl -i http://127.0.0.1:8000/computer/screenshot
```
