# DevLens Production Deployment Readiness

This provider-neutral Aşama 9.3 contract does not provision cloud resources, create production secrets, publish images, or deploy. Provider selection and the first real production smoke belong to Aşama 9.4.

## Target topology

```text
Public Internet
      ↓ HTTPS
Frontend web service (Next.js production container)
      ↓ HTTPS: NEXT_PUBLIC_API_BASE_URL
Backend web service (FastAPI production container)
      ├── GitHub API
      ├── Gemini API
      └── Managed persistent PostgreSQL

Release: database → one-shot `alembic upgrade head` → backend `/health`
          → frontend build/deploy → production browser smoke
```

## Production environment contract

| Variable | Component | Build/runtime | Secret/public | Required | Purpose |
| --- | --- | --- | --- | --- | --- |
| `NEXT_PUBLIC_API_BASE_URL` | Frontend | Build-time | Public | Browser functionality | Public HTTPS FastAPI URL; never a Docker-internal hostname. |
| `CORS_ALLOWED_ORIGINS` | Backend | Runtime | Public configuration | Non-local deployment | Comma-separated exact browser origins. Whitespace is normalized; wildcard/malformed values are rejected. |
| `DATABASE_URL` | Backend/migration | Runtime | Secret | App-optional; production required | `postgresql+asyncpg://USER:PASSWORD@HOST:PORT/DATABASE`. |
| `ANALYSIS_CACHE_TTL_SECONDS` | Backend | Runtime | Non-secret | Optional, default `900` | Deterministic PostgreSQL snapshot cache freshness; `0` disables reads. |
| `GITHUB_TOKEN` | Backend | Runtime | Secret | Optional; recommended for production rate limits | GitHub API bearer token. Never frontend-visible. |
| `GITHUB_API_BASE_URL` | Backend | Runtime | Public configuration | Optional, default `https://api.github.com` | GitHub API endpoint. |
| `GEMINI_API_KEY` | Backend | Runtime | Secret | Optional for startup; needed for AI | Gemini credential. Never frontend-visible. |
| `GEMINI_MODEL` | Backend | Runtime | Non-secret | Optional, default `gemini-2.5-flash` | Gemini model selection. |
| `POSTGRES_DB` | Local Compose | Runtime | Local-only | Local only | Local database name. |
| `POSTGRES_USER` | Local Compose | Runtime | Local-only | Local only | Local database user. |
| `POSTGRES_PASSWORD` | Local Compose | Runtime | Local-only secret | Local only | Local password; never reuse in production. |

`NEXT_PUBLIC_*` is embedded into the browser bundle during `npm run build` and the Docker frontend builder stage. Changing it after image creation requires rebuilding the frontend. No frontend secret may use this prefix.

## Application versus production requirements

The application intentionally remains fail-open/optional in these areas:

- Without `DATABASE_URL`, the API starts and persistence/cache operations remain optional.
- Without `GEMINI_API_KEY`, the API starts and returns a safe unavailable/not-configured AI result.
- Without `GITHUB_TOKEN`, public GitHub requests retain their existing unauthenticated behavior.

Production should still configure persistent PostgreSQL, a GitHub token appropriate for expected rate limits, and Gemini when the full AI experience is required.

## CORS policy

FastAPI uses `CORS_ALLOWED_ORIGINS` as an exact comma-separated allowlist with credentials enabled, `GET`/`POST` methods and all request headers. The local default remains:

```text
http://localhost:3000,http://127.0.0.1:3000
```

Production supplies origins such as `https://frontend.example.com` through runtime configuration. `*` is rejected and is never used with credentialed CORS.

## Services, ports and provider requirements

| Service | Exposure | Port | Contract |
| --- | --- | ---: | --- |
| Frontend | Public HTTPS at provider edge | 3000 | Next.js production `next start`; no local persistence. |
| Backend | Public HTTPS at provider edge | 8000 | Uvicorn production command; `GET /health`; no local persistence. |
| Migration job | Private one-shot backend image | 8000 image context | `alembic upgrade head`; must succeed before backend rollout. |
| PostgreSQL | Private managed service | Provider-managed | PostgreSQL 16-compatible persistent storage, backups and restore. |

The current containers use fixed internal ports 3000 and 8000. Provider selection must support these ports or provide explicit mapping; generic `$PORT` handling was not added speculatively.

The eventual provider must support Docker-compatible frontend/backend services, runtime secrets, HTTPS, health checks, outbound GitHub/Gemini access, managed PostgreSQL and a one-shot migration command. No provider-specific deployment file is included.

## Database and migration release strategy

Production PostgreSQL must persist independently of backend containers. The current async SQLAlchemy engine uses `asyncpg` and `pool_pre_ping=True`; pool tuning belongs to provider deployment. Provider-specific TLS query parameters must be validated in Aşama 9.4.

FastAPI startup does not run migrations. Run from the backend image’s `/app` directory:

```bash
alembic upgrade head
```

Recommended order:

1. Make managed PostgreSQL available and verify backups.
2. Inject backend runtime configuration and secrets.
3. Run the one-shot migration job; stop if it fails.
4. Deploy backend and verify `/health`.
5. Confirm backend public HTTPS URL.
6. Build frontend with `NEXT_PUBLIC_API_BASE_URL` set.
7. Configure the final frontend HTTPS origin in `CORS_ALLOWED_ORIGINS`.
8. Deploy frontend and run browser smoke.
9. Verify GitHub, Gemini, persistence and cache behavior.

Do not automatically run `alembic downgrade` during rollback. Application rollback and schema rollback are separate decisions. Destructive/incompatible changes require a verified managed-database backup and restore plan.

## Health, logging and security boundaries

- `/health` is a fast non-sensitive liveness endpoint returning `{"status":"ok"}`.
- No `/ready` endpoint was added; migration ordering provides schema readiness.
- Production images use Uvicorn and `next start`; no reload/dev command is present.
- Logs go to stdout/stderr. Existing warning logs include request kind and exception type, not DSNs or provider payloads.
- Public errors do not expose SQL, DSNs, stack traces or credentials.
- No broad forwarded-header trust or TrustedHostMiddleware was added without a provider requirement.
- TLS termination belongs to the selected platform edge. Production frontend and backend URLs must both be HTTPS.

## Pre-deploy checklist

- [ ] Final `main` CI is green and production npm audit has zero high/critical findings.
- [ ] Backend runtime secrets are configured through provider secret management.
- [ ] Public backend HTTPS URL is known; frontend was built with it.
- [ ] Final frontend HTTPS origin is in `CORS_ALLOWED_ORIGINS`.
- [ ] Managed PostgreSQL is persistent and its backup/restore policy is understood.
- [ ] `alembic upgrade head` completed successfully.
- [ ] Backend `/health` and frontend health/root are successful.
- [ ] Browser smoke has no mixed-content, console or unexpected network errors.
- [ ] GitHub/Gemini, persistence/cache and rate-limit behavior are verified.
- [ ] No secret appears in image layers, browser bundle or logs.

## Rollback and recovery runbook

- Frontend issue: roll back the frontend image/build.
- Backend issue: roll back the backend image only when schema compatibility is confirmed.
- Migration issue: stop rollout; do not auto-downgrade; assess compatibility and restore a verified backup if required.
- Secret/config issue: correct provider environment/secrets and restart/redeploy the affected service.
- Database recovery: use the managed provider backup/restore procedure; this repository does not implement backups.
- Secret rotation: update provider-managed environment/secrets and restart/redeploy as applicable.

## Non-goals

This stage does not perform cloud deployment, provision PostgreSQL, create production secrets, configure DNS/domains/TLS certificates, publish images, add CD, Kubernetes, Terraform, Redis, workers, auth, observability vendors, or start Aşama 9.4.
