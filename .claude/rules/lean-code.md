# Vex Lean Coding Policy

Bu projede varsayılan yaklaşım minimum ve hedefli değişikliktir.

## Temel kural

İstenen sonucu sağlayan en küçük güvenli değişikliği yap.

Bir dosyayı değiştirmeden önce:
1. İlgili mevcut kodu oku.
2. Kök nedeni belirle.
3. Mevcut fonksiyon, component, utility veya servisle çözülebiliyor mu kontrol et.
4. Sadece gerekli satırları değiştir.

## Varsayılan değişiklik bütçesi

Kullanıcı açıkça daha geniş kapsam istemedikçe:

- En fazla 3 dosya değiştir.
- En fazla 150 satır ekleme/silme yap.
- En fazla 1 yeni dosya oluştur.
- Yeni paket veya dependency ekleme.
- Yeni mimari katman oluşturma.
- İlgisiz kodu yeniden düzenleme.
- Dosya veya sembol isimlerini değiştirme.
- Toplu formatlama yapma.
- Kullanılmayan geleceğe dönük kod ekleme.

Bu sınırların aşılması gerçekten gerekiyorsa kod yazmadan önce:
- neden gerektiğini,
- hangi dosyaların etkileneceğini,
- tahmini diff büyüklüğünü

kısa şekilde bildir.

## Yasak davranışlar

- Çalışan kodu yalnızca daha modern göründüğü için yeniden yazma.
- Tek kullanımlık işlem için yeni abstraction oluşturma.
- Kullanıcı istemeden klasör yapısını değiştirme.
- Kullanıcı istemeden yeni state management sistemi ekleme.
- Kullanıcı istemeden yeni service, manager, provider, factory veya wrapper oluşturma.
- Aynı işi yapan ikinci fonksiyon, hook veya component oluşturma.
- Placeholder, sahte başarı, mock sonuç veya TODO bırakma.
- Hataları any, ts-ignore veya boş except ile gizleme.
- Mevcut görevin dışında hata düzeltme.
- Yalnızca stil amacıyla çalışan kodu değiştirme.
- Bir görevi birden fazla aynı isimli task olarak oluşturma.
- Basit görevler için subagent veya agent team başlatma.

## Yeni dosya oluşturma kuralı

Yeni dosya yalnızca şu durumlarda oluşturulabilir:

1. Kullanıcı açıkça yeni dosya veya modül istedi.
2. Mevcut uygun dosya yok.
3. Mevcut dosyaya eklemek açıkça daha kötü bir sonuç doğuruyor.
4. Yeni dosya görevin doğrudan zorunlu parçası.

Aksi durumda mevcut yapıyı kullan.

## Kod yazmadan önce

Kısa şekilde sadece şunları belirt:

- Kök neden
- Değiştirilecek dosyalar
- En küçük çözüm

Uzun plan veya teorik açıklama üretme.

## Doğrulama

Değişiklikten sonra:

1. `git diff --check` çalıştır.
2. Yalnızca ilgili build veya testi çalıştır.
3. `git diff --stat` kontrol et.
4. Gereksiz değişiklik varsa geri al.
5. Başarı iddiasını gerçek komut sonucuna dayandır.

## Tamamlama formatı

İş bittiğinde yalnızca:

- Düzeltilen sorun
- Değişen dosyalar
- Çalıştırılan test/build
- Varsa kalan risk

bilgisini kısa şekilde ver.
