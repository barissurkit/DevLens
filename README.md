# DevLens

DevLens, ileride public GitHub profillerini ve repository'lerini analiz ederek geliştirici portföyleri hakkında içgörüler sunmayı hedefleyen bir Developer Portfolio Intelligence uygulamasıdır.

## Mevcut aşama

Bu ilk aşamada yalnızca temel proje mimarisi kurulmuştur:

- Next.js + TypeScript + App Router + Tailwind CSS frontend iskeleti
- FastAPI + Pydantic backend iskeleti
- Backend'de temel `GET /health` endpoint'i

GitHub API, AI/Gemini, dashboard ve scoring sistemi aşamalı olarak eklenmiştir; public persistence integration henüz sonraki aşamadadır.

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
