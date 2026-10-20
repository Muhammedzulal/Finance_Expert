# Git ve pull request çalışma kuralları

Proje için branch, commit ve kod inceleme kuralları.

## Branch düzeni

`main` incelenmiş ve çalışır değişiklikleri içerir. İlk faz için ayrı `develop`
branch'i gerekmiyor. Her iş `main` üzerinden açılan kısa ömürlü branch'te yapılır:

- `feat/<konu>`: yeni modül veya özellik
- `fix/<konu>`: hata düzeltme
- `docs/<konu>`: doküman ve sözleşme

Örnek akış (kendi branch adını kullan):

```sh
git switch main
git pull --ff-only origin main
git switch -c docs/json-sozlesmeleri
# Dosyaları düzenle ve doğrula.
git add docs contracts
git commit -m "docs: haber ve analiz veri sözleşmelerini tanımla"
git push -u origin docs/json-sozlesmeleri
```

`main`'e doğrudan push veya force push yapılmaz. PR açılır; proje sorumlusu ya da ilgili
modülün başka bir geliştiricisi inceler. Kimse kendi PR'ını tek başına onaylamaz.
Proje sorumlusunun PR'ını ilgili modül sahiplerinden biri inceler. Başarılı kontroller
ve en az bir inceleme sonrasında squash merge önerilir.

## Commit ve PR içeriği

Commit önekleri: `feat:`, `fix:`, `docs:`, `test:`, `chore:`.
Tek PR tek bir mantıksal işi ele alır. PR açıklamasında sorun, sonuç,
doğrulama komutu ve bilinen eksikler bulunur. JSON alanı değişiyorsa şema,
örnek ve sözleşme dokümanı aynı PR'da güncellenir. İlgili üretici ve tüketici
modül sahipleri sözleşme değişikliğini birlikte inceler.

API anahtarları, .env, .venv, __pycache__, yerel veritabanı ve yeni ham haber
dökümleri eklenmez. Repoda önceden izlenen JSON/pyc dosyalarını .gitignore tek
başına kaldırmaz; bunların temizliği ayrı bir değişiklik olarak ele alınır.

## Önerilen GitHub ayarları

Repo yöneticisi `main` için PR, en az bir onay, çözülmüş yorumlar ve
`validate-contracts` başarılı kontrolünü zorunlu kılsın; force push'u kapatsın.
Bu ayarlar öneridir; bu teslimde GitHub branch koruması değiştirilmemiştir.
