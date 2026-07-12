---
name: minimal-fix
description: Mevcut kodda en küçük güvenli değişiklikle hata veya dar kapsamlı görev çözümü yapar.
argument-hint: "[çözülecek sorun]"
disable-model-invocation: true
disallowed-tools: Agent
---

# Minimal Fix Mode

Görev:

$ARGUMENTS

Bu görevde minimum değişiklik yaklaşımı zorunludur.

## Çalışma sırası

1. Önce `git status --short` çalıştır.
2. Kullanıcının mevcut değişikliklerini tespit et ve koru.
3. İlgili dosyaları bul.
4. Sorunun kök nedenini belirle.
5. Mevcut kodla çözülebilen en küçük çözümü seç.
6. Sadece gerekli satırları değiştir.
7. İlgili test veya build komutunu çalıştır.
8. `git diff --check` çalıştır.
9. `git diff --stat` çalıştır.
10. Diff'i incele ve gereksiz değişiklikleri geri al.

## Kesin sınırlar

Kullanıcı daha geniş kapsamı açıkça istemediyse:

- En fazla 3 dosya değiştir.
- En fazla 150 eklenen/silinen satır.
- En fazla 1 yeni dosya.
- Yeni dependency ekleme.
- Yeni abstraction oluşturma.
- İlgisiz refactor yapma.
- Dosya taşımama veya isim değiştirmeme.
- Toplu formatlama yapmama.
- Agent veya subagent başlatmama.
- Gelecekte kullanılabilecek kod yazmama.

Limit aşılması gerekiyorsa herhangi bir dosyayı değiştirmeden önce dur ve nedenini açıkla.

## Karar kriteri

İki çözüm aynı sonucu sağlıyorsa:

- Daha az dosya değiştiren,
- Daha az satır ekleyen,
- Mevcut yapıyı kullanan,
- Daha kolay geri alınabilen

çözümü seç.

## Son rapor

Yalnızca şu formatı kullan:

Kök neden:
- ...

Düzeltme:
- ...

Değişen dosyalar:
- ...

Doğrulama:
- ...

Diff:
- ... dosya, ... ekleme, ... silme
