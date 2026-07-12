# Visible Code Changes Policy

Bu projedeki bütün kod ve yapılandırma değişiklikleri kullanıcı tarafından görünür ve incelenebilir olmalıdır.

## Zorunlu dosya düzenleme yöntemi

Kod veya metin dosyalarını değiştirmek için Claude Code'un kendi:

- Edit
- Write
- NotebookEdit

araçlarını kullan.

Dosya içeriğini değiştirmek için Bash kullanma.

Aşağıdaki yöntemlerle dosya oluşturma veya düzenleme:

- `cat > file`
- `cat <<EOF`
- `echo ... > file`
- `sed -i`
- `perl -pi`
- `python` ile dosyayı yeniden yazma
- shell script ile toplu patch
- `apply_patch` komutunu Bash üzerinden çalıştırma
- `cp` ile mevcut dosyanın üzerine yazma
- `mv` ile dosya değişikliğini gizleme

Bu yöntemler kullanıcının önerilen değişikliği VS Code diff ekranında kabul etmeden önce görmesini engelleyebilir.

## Her düzenlemeden önce

Dosya değiştirmeden önce kısa şekilde bildir:

- Değiştirilecek dosya
- Değişiklik amacı
- Tahmini değişen satır miktarı

Uzun açıklama yapma.

## Düzenleme kapsamı

- Bir seferde yalnızca bir dosya düzenle.
- Kullanıcı diff'i kabul etmeden sonraki dosyaya geçme.
- İlgisiz kodu değiştirme.
- Toplu formatlama yapma.
- Kullanıcı istemeden dosya taşıma veya yeniden adlandırma yapma.
- Kullanıcı istemeden yeni dosya oluşturma.

## Düzenleme sonrası

Her dosya değişikliğinden sonra:

1. Değişikliğin kabul edilmesini bekle.
2. Kabul edilirse ilgili test veya build'i çalıştır.
3. Görev sonunda `git diff --stat` çalıştır.
4. Değişen dosyaları listele.
5. Eklenen ve silinen satır sayısını bildir.

## Başarı ölçütü

Kullanıcı:

- Hangi dosyanın değiştiğini,
- Hangi satırların eklendiğini,
- Hangi satırların silindiğini,
- Değişikliğin neden yapıldığını

görebilmelidir.
