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
## Patch Geçmişi

### Patch 01 — Kritik Backend Onarımları
- `/chat` artık frontend'in gönderdiği `history`'yi prompt'a dahil ediyor;
  Gemini hatasında `success:false` + açıklayıcı `reply` dönüyor.
- Ekran analizi (`/screen/capture-and-analyze`, `/computer/observe`)
  görüntüyü gerçekten Gemini'ye gönderiyor.
- Computer-use motoru legacy'den modüler yapıya taşındı:
  `/computer/task`, `/computer/observe`, `/computer/action`,
  `/computer/step/approve`, `/computer/step/reject` geri geldi
  (intent router, allowlist, self-UI koruması, manuel adım onayı).
- `json_store` atomik yazma + kilit + bozuk dosya yedeği yapıyor.
- Hatırlatıcı zaman ayrıştırma genişledi ("yarın 15:00", "bugün 18.30",
  hafta günleri); anlaşılamayan ifade nota düşülüyor.
- Runtime json verileri `vex-backend/data/` altına taşındı
  (`VEX_DATA_DIR` ile değiştirilebilir); eski `main.*.py` yedekleri
  `_archive/legacy/` altına alındı.
- Modeller `.env` üzerinden: `GEMINI_MODEL`, `GEMINI_VISION_MODEL`.
