# Vex Project Instructions

## Proje yapısı
Bu proje iki ana parçadan oluşur:

- Frontend: ./vex-app
- Backend: ./vex-backend

Kök klasör:
- /Users/mert/Vex

Frontend package.json:
- /Users/mert/Vex/vex-app/package.json

Backend ana dosya:
- /Users/mert/Vex/vex-backend/main.py

## Dil ve cevap tarzı
- Kullanıcıya Türkçe cevap ver.
- Gereksiz uzun açıklama yapma.
- Kod değişikliklerinden önce kısa plan çıkar.
- Kullanıcı onaylamadan büyük refactor yapma.
- Kod değişikliklerinde mümkünse tam dosya içeriği ver.
- Terminal komutlarını mümkün olduğunca tek blok halinde ver.

## Mutlak kurallar
- .env dosyasını silme.
- API key/token/secret değerlerini terminale yazdırma.
- Gereksiz paket güncellemesi yapma.
- Frontend/backend bağlantısını bozma.
- Production veya riskli ayarları değiştirme.
- Veritabanı, migration, delete/drop gibi işlemler için kullanıcıdan onay almadan işlem yapma.

## Frontend
Frontend klasörü:
./vex-app

Frontend komutları bu klasörde çalıştırılmalı:
cd /Users/mert/Vex/vex-app

Örnek:
npm run dev
npm run build

## Backend
Backend klasörü:
./vex-backend

Backend komutları bu klasörde çalıştırılmalı:
cd /Users/mert/Vex/vex-backend

Backend FastAPI/Python yapısındadır. main.py dosyasını kontrol etmeden backend komutu varsayma.

## Çalışma akışı
1. Önce proje dosya yapısını analiz et.
2. Frontend ve backend scriptlerini oku.
3. Kod değiştirmeden önce kısa plan çıkar.
4. Sadece gerekli dosyaları değiştir.
5. Değişiklikten sonra build/test çalıştır.
6. Hata çıkarsa kök sebebi bulup düzelt.
7. Sonunda değişen dosyaları özetle.

## Özel beklenti
Bu projede frontend ve backend tek komutla birlikte başlatılabilmeli. Var olan start-vex.sh dosyasını kontrol et. Gerekirse güvenli şekilde düzelt.
