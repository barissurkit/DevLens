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

## Docker ile local production-like ortam

Docker Compose kurulumu, cloud deployment değildir; DevLens'in local production-like çalışma ortamıdır. Docker ve Docker Compose Plugin gerektirir. Varsayılan olarak yalnız frontend (`3000`) ve backend (`8000`) host'a açılır; PostgreSQL host portuna açılmaz.

Güvenli yerel ayarları kopyalayıp gerektiğinde değiştirin:

```bash
cp .env.example .env
docker compose config
docker compose build
docker compose up -d
docker compose ps
```

Tarayıcıdan [http://localhost:3000](http://localhost:3000), backend sağlık kontrolünden [http://localhost:8000/health](http://localhost:8000/health) erişilebilir. Logları görmek ve ortamı durdurmak için:

```bash
docker compose logs -f backend frontend migrate
docker compose down
```

Compose akışı PostgreSQL healthcheck'i ile başlar; `migrate` servisi ayrı bir one-shot container olarak `alembic upgrade head` çalıştırır. Migration başarılı olmadan backend başlamaz; FastAPI import/startup sırasında migration çalıştırmaz. PostgreSQL verisi `devlens-postgres-data` named volume'unda tutulur. Şemayı ve yerel cache snapshot'larını sıfırlamak isterseniz, bunun veri sileceğini bilerek:

```bash
docker compose down -v
```

Compose ortamında backend `DATABASE_URL` için Docker içindeki `db` hostname'ini kullanır. Frontend build'ine yalnız browser'ın erişebileceği `NEXT_PUBLIC_API_BASE_URL` (`http://localhost:8000`) girer; GitHub/Gemini anahtarları yalnız backend runtime environment'ında bulunur. `ANALYSIS_CACHE_TTL_SECONDS` varsayılan olarak 900 saniyedir; deterministic analysis cache PostgreSQL named volume sayesinde backend process/container restart'larından sonra da korunur. Interpretation ve recommendation cache'lenmez; DB operasyonları mevcut fail-open politikasını korur.

## CI quality gates

Pull requests targeting `main` and pushes to `main` run the GitHub Actions `CI` workflow. It validates the backend regression suite, disposable PostgreSQL/Alembic integration, frontend lint/type-check/build and production dependency security, plus the Docker production-stack startup smoke. The stable `Required quality gates` aggregate check is required before merging to `main`. CI does not deploy and does not use production GitHub, Gemini, or database secrets.

## Production deployment readiness

Provider-neutral production configuration, environment classification, CORS policy, migration release order, rollback guidance and the pre-deploy checklist are documented in [docs/production-deployment.md](docs/production-deployment.md). This document prepares a future deployment; it does not provision cloud resources or perform a deployment.
