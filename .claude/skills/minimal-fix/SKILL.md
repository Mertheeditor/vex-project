---
name: minimal-fix
description: Bir hatayı mümkün olan en küçük, güvenli ve doğrulanabilir değişiklikle düzeltir.
---

# Minimal Fix

Bir hata veya küçük kapsamlı sorun çözülürken bu skill kullanılmalıdır.

## Amaç

Sorunu gideren en küçük değişikliği uygulamak; ilgisiz refactor, yeniden adlandırma,
formatlama veya mimari değişiklik yapmamak.

## Zorunlu Akış

1. Sorunu ve beklenen davranışı tanımla.
2. Etkilenen dosyaları oku.
3. Kök nedeni belirle.
4. En küçük güvenli değişikliği uygula.
5. İlgili testleri ve syntax kontrollerini çalıştır.
6. `git diff --check` çalıştır.
7. Değişen dosyaları ve doğrulama sonucunu raporla.

## Sınırlar

- İlgisiz dosyaları değiştirme.
- Test silerek veya gevşeterek başarı sağlama.
- Hata çıktısını gizleme.
- Yeni dependency ekleme.
- `.env`, secret, token veya credential dosyalarını okuma.
- Push, deploy, force push, rebase veya destructive Git işlemi yapma.
- Kullanıcı onayı olmadan dış sistemlerde geri döndürülemez işlem yapma.

## Başarı Ölçütü

- Sorun yeniden üretilebilir şekilde giderilmiş olmalı.
- Mevcut davranış gereksiz yere değiştirilmemeli.
- İlgili testler geçmeli.
- Diff küçük, anlaşılır ve geri alınabilir olmalı.
