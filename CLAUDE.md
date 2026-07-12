# Vex Project Instructions

## Proje mimarisi
- Kök: `/Users/mert/Vex`
- Frontend: `/Users/mert/Vex/vex-app`
- Backend: `/Users/mert/Vex/vex-backend`
- Frontend stack: React 19, TypeScript, Vite 7, Tauri 2
- Backend stack: Python, FastAPI, Uvicorn
- Frontend adresi: `http://localhost:1420`
- Backend adresi: `http://127.0.0.1:8000`
- Ana başlangıç scripti: `/Users/mert/Vex/start-vex.sh`

## Genel çalışma akışı
1. Önce yalnızca görevle ilgili klasörleri incele.
2. Dosya, fonksiyon, route veya ayar tahmin etme; arayıp doğrula.
3. En küçük ama eksiksiz değişikliği yap.
4. İlgisiz refactor yapma.
5. Değişiklikten sonra yalnızca ilgili kontrolleri çalıştır.
6. Sonuçta sadece değişiklikleri ve test/doğrulama sonuçlarını özetle.

## Genel kurallar
- Kullanıcıya Türkçe ve kısa cevap ver.
- Kod değişikliğinden önce kısa plan çıkar.
- Kullanıcı onaylamadan büyük refactor yapma.
- Bir görev için tüm projeyi tarama; sadece ilgili alanları incele.
- Çalışan özellikleri sessizce kaldırma.
- Geçici mock, sahte başarı cevabı veya kök nedeni gizleyen geniş hata bastırmaları ekleme.
- Hata varsa kök nedeni çözmeden görev tamamlandı deme.
- Uygulama kodunu sohbette tamamen yazdırmak yerine dosyaları doğrudan düzenle.
- Aynı oturumda tek ana görev üzerinde kal; yeni ve ilgisiz görevde temiz bağlam tercih et.
- Uzun görevlerde compact özette görev, kök neden, değiştirilen dosyalar ve test sonuçlarını koru.

## Güvenlik ve sınırlar
- `.env` dosyalarını silme, içeriklerini okuma veya çıktıya yazdırma.
- API key, token ve secret değerlerini terminale basma.
- Gereksiz paket güncellemesi yapma.
- Frontend/backend bağlantısını bozma.
- Production veya riskli ayarları değiştirme.
- Kullanıcı onayı olmadan migration, delete/drop veya dosya silme işlemi yapma.
- `start-vex.sh` scriptini yalnızca doğrulanmış bariz bir sorun varsa değiştir.

## Doğrulama ilkesi
- Frontend komutlarını `vex-app` altında çalıştır.
- Backend komutlarını `vex-backend` altında çalıştır.
- Var olmayan script veya araç uydurma.
- Frontend için mevcut doğrulama yüzeyi `package.json` içindeki komutlardır.
- Backend için mevcut doğrulama yüzeyi giriş dosyası, import/syntax ve health endpointleridir.

## Ek kurallar
Detaylı ve path-specific kurallar için:
- `.claude/rules/frontend.md`
- `.claude/rules/backend.md`
- `.claude/rules/safety.md`
- `.claude/rules/verification.md`

Kısa repo komutları için:
- `.claude/commands/vex-analyze.md`
- `.claude/commands/vex-fix.md`
- `.claude/commands/vex-check.md`
