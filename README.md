# Vex

Vex; Tauri + React (frontend) ve FastAPI (backend) ile geliştirilen,
local-first çalışan kişisel yapay zeka iş arkadaşıdır. Proje/görev/onay/
hatırlatıcı takibi, Gemini ile sohbet, yerel Whisper ile ses tanıma,
ekran analizi ve onaylı bilgisayar kontrolü içerir.

## Mimari

- `vex-app/` — React + TypeScript + Vite + Tauri masaüstü arayüzü
- `vex-backend/` — FastAPI (127.0.0.1:8000), modüler yapı:
  `app/routes` → `app/services` → `app/storage` → `app/core`
- `vex-backend/data/` — runtime json verileri ve screenshotlar
  (kişisel veri içerir, git'e girmez)

## Kurulum

Backend:

```bash
cd vex-backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # GEMINI_API_KEY değerini doldur
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Frontend:

```bash
cd vex-app
npm install
npm run tauri dev
```

Tek komutla (macOS): repo kökünde `./start-vex.sh`

## Hızlı test

```bash
curl -i http://127.0.0.1:8000/health
curl -i http://127.0.0.1:8000/computer/status
curl -s -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Merhaba","history":[]}'
```

## Notlar

- Gemini, Whisper, sounddevice, mss ve pyautogui eksikse backend çökmez;
  ilgili endpoint anlamlı hata döner (bkz. `app/core/optional_imports.py`).
- Riskli işlemler (ör. Shopify yayına alma, manuel bilgisayar adımları)
  onay mekanizmasından geçer.
- Eski monolitik `main.py` yedekleri `_archive/` altındadır ve git'e girmez.
