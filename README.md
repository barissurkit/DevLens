# DevLens

DevLens, public GitHub profillerini ve repository'lerini analiz ederek geliştirici portföyleri hakkında içgörüler sunan bir Developer Portfolio Intelligence uygulamasıdır.

## Mevcut durum

DevLens; GitHub portföy analizi, isteğe bağlı Gemini yorumu, scoring ve PostgreSQL snapshot persistence akışlarını içerir. Public API sözleşmesi `GET /health`, `POST /api/v1/analysis` ve `POST /api/v1/interpretation` endpoint'lerinden oluşur.

## Teknoloji stack'i

- **Frontend:** Next.js, TypeScript, Tailwind CSS
- **Backend:** Python, FastAPI, Pydantic, Uvicorn
- **Persistence:** PostgreSQL, async SQLAlchemy, asyncpg, Alembic

## Frontend'i çalıştırma

```bash
cd frontend
npm install
npm run dev
```

Ardından [http://localhost:3000](http://localhost:3000) adresini açın.

## Backend'i çalıştırma

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Sağlık kontrolü için [http://localhost:8000/health](http://localhost:8000/health) adresini kullanabilirsiniz. Beklenen yanıt:

```json
{"status":"ok"}
```

`DATABASE_URL` persistence foundation için isteğe bağlıdır; örnek değer `.env.example` içindedir. Migration çalıştırmak için PostgreSQL erişilebilirken:

```bash
cd backend
alembic upgrade head
```

`DATABASE_URL` yapılandırılmışsa başarılı public analysis sonuçları snapshot olarak yazılır. `/analysis` analysis-only, `/interpretation` ise tek bir composite snapshot yazar; AI kullanılamadığında oluşan geçerli unavailable sonucu da korunur. Veritabanı yapılandırılmadığında uygulama mevcut şekilde çalışır ve beklenen persistence altyapı hataları public sonucu bozmaz.

Snapshot store artık deterministic analysis için 15 dakikalık freshness cache olarak da kullanılabilir. `ANALYSIS_CACHE_TTL_SECONDS` varsayılanı 900'dür; `0` cache okumalarını kapatır ancak yeni snapshot yazımlarını kapatmaz. Yalnız deterministic analysis reuse edilir; Gemini interpretation ve recommendation cache'lenmez. Stale snapshot GitHub hatasında fallback olarak kullanılmaz. Redis veya process-memory cache yoktur.

Cache yalnızca PostgreSQL-backed deterministic analysis reuse sağlar; uygulama yeniden başlatıldığında da geçerliliğini korur. Persistence ve cache veritabanı operasyonları beklenen bağlantı/SQLAlchemy hatalarında fail-open davranır; GitHub veya Gemini uygulama hataları sessizce yutulmaz.

V1 sınırlamaları: manual force refresh, interpretation cache, stale-if-error, retention policy, public history/metrics, public cache metadata ve distributed request coalescing yoktur. Aynı kullanıcı için eşzamanlı cold miss'ler birden fazla GitHub analizi ve snapshot üretebilir.
