# Finance Expert - 3. hafta Docker Compose kurulumu

Bu dosyalar **mevcut projeye ekleme** icindir. Docker Compose tum sistemi
ayri bir gelistirme ortaminda calistirir: MySQL + FastAPI + Ollama + AI worker.

## Neden baska port kullaniyoruz?

- Senin mevcut `finance-expert-mysql` konteynerin **3307** portunda calisiyor.
- Bu Compose yeni MySQL icin **3308** portunu kullanir.
- Var olan FastAPI **8000**'de calisiyor; Compose FastAPI ise **8001**'de acilir.
- Yeni veritabani **ayri ve baslangicta bos**. Eski `wallet:1` ve islemler buna kopyalanmaz.
- `docker compose down -v` **KULLANMA**: yeni Compose verilerini silebilir.

## Gereken mevcut proje dosyalari

Bu ZIP'teki dosyalar proje kokune kopyalanmali (ornegin `Finance_Expert/`).
Su dosyalar mevcut olmali:

- `backend/main.py` (3. haftada duzenledigimiz surum)
- `backend/database.py`
- `ai/worker.py`, `ai/analiz.py`, `ai/piyasa.py`
- `contracts/finance-v1.schema.json`
- `database/finance_expert_schema.sql`

Eger `ai/worker.py` bilgisayarinda yoksa ana daldaki guncel AI kodunu
almadan bu kurulumda AI worker olusturulamaz. **Var olan degisikliklerini
yedeklemeden git pull/checkout yapma.**

## Git Bash - komutlar

```
cd ~/Desktop/Finance_Expert
ls backend/main.py ai/worker.py contracts/finance-v1.schema.json database/finance_expert_schema.sql
python tools/setup_compose_env.py
docker compose --env-file .env.compose config --quiet
docker compose --env-file .env.compose up -d --build
```

Bu komutlardan herhangi biri hata verirse sonraki komuta gecme.
Ilk build internetle paket ve Docker imaji indirecegi icin zaman alabilir.

## Test

```
docker compose --env-file .env.compose ps
```

- Compose backend: http://127.0.0.1:8001/docs
- DB testi: http://127.0.0.1:8001/health/db
- Compose MySQL: `localhost:3308`, **eski MySQL ile karistirma**.

Ollama modeli kurulu degilse worker modeli bekler, bu bir hata degildir.
Modeli **bir kez** indirmek icin:

```
docker compose --env-file .env.compose exec ollama ollama pull qwen3.5:4b
```

Daha sonra worker logunu kontrol et:

```
docker compose --env-file .env.compose logs --tail=40 ai_worker
```

Worker'inin gercek haber analizi icin haber verisine, modelin indirilmeye ve
backend API ile uyumlu JSON sozlesmesine ihtiyaci var.

## Durdurma (veriler silinmez)

```
docker compose --env-file .env.compose down
```

`down -v` yazma. Eski `finance-expert-mysql` konteynerine `docker rm` uygulama.
Bu kurulum senin mevcut verilerini kullanmaz; eski Swagger 8000'deki testlerin
bu yeni MySQL'de gorunmemesi NORMALDIR.
