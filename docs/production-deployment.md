# Production Deployment

This document describes the current DevLens production topology and operational boundaries. It contains no credentials, provider resource IDs, or private service URLs.

## Current Topology

```text
User Browser
      ↓ HTTPS
Render Free — Next.js production frontend
      ↓ HTTPS direct fetch via NEXT_PUBLIC_API_BASE_URL
Render Free — FastAPI/Uvicorn backend
      ├── HTTPS → GitHub API
      ├── PostgreSQL/TLS → Neon Free PostgreSQL
      └── HTTPS → Gemini API (optional interpretation)

Separate release operation:
backend image/environment → Alembic one-shot migration → Neon schema
```

The frontend contains no GitHub, Gemini, or database secrets. Provider credentials belong to the backend runtime. `CORS_ALLOWED_ORIGINS` restricts browser access to explicit frontend origins.

## Production Services

| Service | Current deployment | Runtime contract |
| --- | --- | --- |
| Frontend | Render Free | Next.js production `next start`, port 3000 |
| Backend | Render Free | FastAPI/Uvicorn, port 8000, `GET /health` |
| Database | Neon Free PostgreSQL | Persistent PostgreSQL-compatible storage |
| Migration | One-shot backend image operation | `alembic upgrade head` before backend rollout |
| GitHub | GitHub API | Public evidence; optional backend-only token |
| AI | Gemini API | Optional interpretation, model `gemini-3.6-flash` |

## Environment Variables

| Variable | Component | Visibility | Purpose |
| --- | --- | --- | --- |
| `NEXT_PUBLIC_API_BASE_URL` | Frontend build | Public | Public HTTPS FastAPI URL |
| `CORS_ALLOWED_ORIGINS` | Backend runtime | Public configuration | Exact allowed frontend origins |
| `DATABASE_URL` | Backend/migration | Secret | Neon PostgreSQL connection |
| `GITHUB_TOKEN` | Backend runtime | Secret | Optional GitHub API bearer token |
| `GITHUB_API_BASE_URL` | Backend runtime | Public configuration | Defaults to `https://api.github.com` |
| `GEMINI_API_KEY` | Backend runtime | Secret | Optional Gemini credential |
| `GEMINI_MODEL` | Backend runtime | Non-secret | Defaults to `gemini-3.6-flash` |
| `ANALYSIS_CACHE_TTL_SECONDS` | Backend runtime | Non-secret | Defaults to `900` seconds |

`NEXT_PUBLIC_API_BASE_URL` is embedded into the frontend build and must never contain a secret. See [.env.example](../.env.example) for local configuration names.

## Database Migration

FastAPI startup does not run migrations. Run migration as a separate one-shot operation using the backend image and production database environment:

```bash
alembic upgrade head
```

Stop the rollout if migration fails. The application uses SQLAlchemy with `asyncpg`; schema changes and application rollbacks remain separate decisions. Do not automatically downgrade production schema during rollback.

## Deployment Order

1. Confirm Neon PostgreSQL availability and backup/restore expectations.
2. Configure backend runtime secrets and public settings.
3. Run the one-shot Alembic migration.
4. Deploy or restart the backend and verify `/health`.
5. Build the frontend with the public backend URL.
6. Configure the production frontend origin in `CORS_ALLOWED_ORIGINS`.
7. Deploy the frontend.
8. Run browser smoke and verify GitHub, cache, persistence, and optional Gemini behavior.

## Health Verification

`GET /health` is a fast non-sensitive liveness endpoint returning:

```json
{"status":"ok"}
```

Normal application responses include a server-generated `X-Request-ID`. Structured logs correlate request lifecycle and provider activity; this document does not claim that every possible raw unhandled 500 response has the header.

## Analysis Verification

`POST /api/v1/analysis` returns deterministic repository and portfolio analysis. The PostgreSQL snapshot cache reuses only fresh snapshots with compatible schema and `ANALYSIS_ENGINE_VERSION` (`v2`). The default freshness window is 900 seconds. Supported cache read failures fail open, and persistence writes are best-effort.

## Interpretation Verification

`POST /api/v1/interpretation` reuses deterministic analysis where available, then may invoke Gemini again. A persisted interpretation payload is not described as a reusable AI cache authority. Gemini output is schema- and signal-reference-validated, and unavailable AI leaves deterministic analysis usable.

The configured default model is `gemini-3.6-flash`. Natural-language output is Turkish while repository names, technology names, package names, URLs, and technical identifiers are preserved.

## Rollback / Safety Notes

- Frontend issues can be rolled back at the frontend deployment level.
- Backend rollback requires schema compatibility confirmation.
- Migration failure stops rollout; do not auto-downgrade.
- Secret rotation uses provider-managed runtime configuration followed by service restart/redeploy.
- Database recovery uses Neon managed backup/restore procedures.
- Do not expose tokens, DSNs, credentials, provider resource IDs, or internal URLs in logs or public documentation.

## Cost Assumptions

Expected recurring infrastructure cost under the current free-tier configuration: **$0/month**. This is not a guaranteed operating cost; provider pricing, quotas, free-tier policies, and usage limits may change.

## Related Documentation

- [Architecture and technical story](architecture.md)
- [Project README](../README.md)
- [Environment template](../.env.example)
