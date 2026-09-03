# DevLens — Recruiter / Social Package

Reusable communication copy for recruiter conversations, LinkedIn, CVs, portfolio pages, and technical interviews. Claims in this document match the [README](../README.md), [case study](case-study.md), [architecture](architecture.md), and [production deployment](production-deployment.md) documentation.

## LinkedIn Version A — Turkish

DevLens adında bir full-stack proje geliştirdim. Amaç, herkese açık GitHub repository’lerindeki mühendislik sinyallerini daha düzenli ve açıklanabilir hale getirmekti. GitHub profillerini yalnızca star veya fork sayılarıyla değerlendirmek yerine README yapısı, test ve CI izleri, repository hygiene, dependency manifest’leri ve proje yapısı gibi gözlemlenebilir kanıtları analiz ediyor.

Projede özellikle deterministic analysis ve AI interpretation katmanlarını birbirinden ayırdım. Repository ve portfolio sinyalleri, skorlar ve limitations deterministic kurallarla üretiliyor. Böylece aynı desteklenen kanıtlar için sonuçlar tekrarlanabilir, incelenebilir ve regression test’leriyle doğrulanabilir kalıyor. Gemini ise skor hesaplayan bir katman değil; deterministic sonuçlardan oluşturulan structured context’i açıklayan ve improvement sinyallerine dayalı, sınırları belirli bir sonraki proje önerisi üreten optional bir interpretation katmanı.

Ürün, Next.js/React/TypeScript frontend ile FastAPI/Python backend’den oluşuyor. Backend GitHub API’ye erişiyor, repository’leri bounded concurrency ile analiz ediyor ve deterministic snapshot’ları PostgreSQL’de TTL, schema compatibility ve `ANALYSIS_ENGINE_VERSION` kontrolleriyle saklıyor. Gemini veya persistence kullanılamadığında temel deterministic analysis’in kullanılabilir kalması için partial-success ve best-effort davranışları uygulanıyor.

Uygulama Render üzerinde frontend ve backend servisleri, Neon PostgreSQL ve ayrı one-shot Alembic migration akışıyla production’da çalışıyor. Bu proje bana yalnızca bir UI değil; external API sınırları, reproducible scoring, version-aware cache, constrained LLM integration, async provider erişimi, structured observability ve privacy-aware telemetry kararlarını birlikte tasarlama pratiği kazandırdı.

Buradaki önemli nokta, AI kullanmanın deterministic davranıştan vazgeçmek anlamına gelmemesi. Gemini yanıtı beklenmeyen şekilde dönerse veya provider kullanılamazsa, kullanıcı yine hangi repository kanıtlarının bulunduğunu ve hangi alanlarda kısmi veri olduğunu görebiliyor. Bu yaklaşım, ürünü bir “AI sonucu” yerine sınırları belli bir analysis sistemi olarak düşünmeme yardımcı oldu. Projenin [case study ve architecture dokümanlarını](case-study.md) da bu ayrımı açıkça anlatacak şekilde hazırladım.

## LinkedIn Version B — English

I built DevLens as a full-stack project for making public GitHub portfolio evidence easier to inspect. Instead of treating stars or forks as engineering quality, it analyzes observable signals such as README structure, testing and CI traces, repository hygiene, dependency manifests, and project structure.

One of the main design decisions was separating deterministic analysis from AI interpretation. Repository and portfolio signals, scores, findings, and limitations are produced by deterministic rules, so supported evidence remains repeatable, inspectable, and suitable for regression testing. Gemini is not the scoring engine. It receives a structured context derived from deterministic results and provides optional natural-language interpretation plus a bounded next-project recommendation grounded in improvement signals.

The product uses a Next.js/React/TypeScript frontend and a FastAPI/Python backend. The backend integrates with the GitHub API, analyzes repositories with bounded concurrency, and stores deterministic snapshots in PostgreSQL with TTL, schema compatibility, and `ANALYSIS_ENGINE_VERSION` checks. Supported Gemini or persistence failures do not necessarily remove the useful deterministic result.

The application is production-deployed with separate Render frontend and backend services, Neon PostgreSQL, and a one-shot Alembic migration flow. The project demonstrates concrete engineering decisions around external API boundaries, reproducible scoring, version-aware caching, constrained LLM integration, async provider access, structured observability, and privacy-aware telemetry.

The result is deliberately not presented as a hiring score or a complete developer assessment. It is a tool for making supported public evidence easier to inspect and discuss. That distinction shaped both the product language and the implementation: limitations are returned with the analysis, partial evidence is visible, and the optional AI layer cannot become an untraceable source of scores. I also documented the architecture and production decisions so the repository can be read as an engineering project, not only as a UI demo.

## CV Project Description

### Short CV Version

- Built a production-deployed Next.js and FastAPI application that analyzes public GitHub repository evidence with deterministic, explainable scoring.
- Designed a version-aware PostgreSQL snapshot cache and constrained Gemini interpretation layer with graceful AI degradation.

### Detailed CV Version

- Built a full-stack DevLens application with a Next.js/React/TypeScript frontend and FastAPI/Python backend for evidence-based public GitHub portfolio analysis.
- Designed a deterministic analysis engine for documentation, testing/automation, repository hygiene, repository scoring, portfolio aggregation, findings, and limitations; kept Gemini outside scoring authority.
- Implemented async GitHub integration with bounded repository concurrency and PostgreSQL JSONB snapshots using SQLAlchemy, asyncpg, Alembic, TTL, schema compatibility, and engine-version checks.
- Deployed separate frontend/backend services on Render with Neon PostgreSQL, one-shot migrations, structured observability, protected CI gates, and optional schema-validated Gemini interpretation.

## Portfolio Website Copy

### Project Card

**Title:** DevLens

**One-line summary:** Evidence-based public GitHub portfolio analysis with deterministic scoring and optional Gemini interpretation.

**Short description:** A production-deployed Next.js and FastAPI application that turns observable GitHub repository signals into explainable repository and portfolio findings.

**Tech stack:** Next.js, React, TypeScript, Tailwind CSS, FastAPI, Python, PostgreSQL, SQLAlchemy, asyncpg, Alembic, GitHub API, Gemini, Docker, Render, Neon.

**Highlights:**

- Deterministic scoring authority
- Optional constrained AI interpretation
- Version-aware PostgreSQL snapshot cache
- Bounded asynchronous repository analysis
- Partial-success and privacy-aware observability model

### Project Detail Intro

DevLens is a full-stack application that analyzes observable evidence from public GitHub portfolios. Its central design choice is to keep evidence extraction, repository scoring, portfolio aggregation, findings, and limitations deterministic rather than delegating them to an LLM. This makes the core result repeatable and traceable to supported repository signals. Gemini is an optional second layer that receives structured deterministic context and explains the findings in natural language without creating evidence or changing scores. The system uses a Next.js frontend, FastAPI backend, GitHub API integration, PostgreSQL snapshot persistence, bounded repository concurrency, and a version-aware cache. It is deployed as separate Render services with Neon PostgreSQL and a one-shot Alembic migration flow.

## Recruiter Pitch

### 15-second version

I built DevLens, a production-deployed tool that analyzes public GitHub repository evidence with deterministic scoring. Gemini is an optional layer for explaining those findings, not for deciding the scores.

### 30-second version

DevLens helps make GitHub portfolio review more evidence-based. A Next.js frontend sends a username to a FastAPI backend, which analyzes repository documentation, testing, and hygiene signals deterministically. PostgreSQL stores versioned snapshots, while Gemini can optionally explain the structured results and suggest a bounded next project. The main technical distinction is the clear separation between reproducible scoring and optional AI interpretation.

### 60-second version

DevLens addresses the difficulty of reviewing many GitHub repositories quickly without confusing popularity with engineering evidence. The browser calls a Next.js frontend and FastAPI backend, which fetches public GitHub data and analyzes eligible repositories with bounded concurrency. Deterministic rules produce repository signals, scores, portfolio aggregation, findings, and limitations. PostgreSQL stores fresh, schema-compatible, engine-compatible snapshots to reduce repeated GitHub work. Gemini is optional and receives only a structured deterministic context, so it can explain supplied signals but cannot create evidence or change scores. The production system runs as separate Render frontend and backend services with Neon PostgreSQL and a one-shot Alembic migration. If the AI provider is unavailable, the deterministic analysis remains useful.

## Technical Interview Project Explanation

### English — Approximately Two Minutes

DevLens started with a simple problem: a GitHub portfolio contains useful engineering evidence, but reviewing it consistently takes time, and popularity metrics do not explain repository quality. I designed the product around a deterministic core rather than asking an LLM to judge a developer.

The user enters a GitHub username in the browser. The Next.js frontend sends the request directly to the FastAPI backend, where the username is normalized and validated. The backend first checks PostgreSQL for a fresh snapshot compatible with the current analysis schema and engine version. On a miss, it fetches the public GitHub profile and repositories, excludes forks and archived repositories, and analyzes selected repositories with bounded concurrency.

For each repository, the pipeline examines the README, recursive tree, and selected dependency manifests. It detects documentation, testing, CI, hygiene, technology, and category signals. Repository scores, portfolio aggregation, portfolio scoring, intelligence, and limitations are then produced deterministically. This gives the product repeatability, evidence traceability, and provider independence for its core result.

Gemini is intentionally downstream of that process. The backend builds a reduced structured interpretation context and sends it to Gemini only when the optional provider is configured. Gemini can explain deterministic strengths and improvement areas and produce a grounded recommendation, but schema and signal-reference validation prevents it from inventing evidence or modifying scores. If Gemini is unavailable, the API returns a stable unavailable state while preserving deterministic analysis.

Snapshots are persisted in PostgreSQL JSONB with a 900-second default TTL, `analysis_generated_at`, schema compatibility, and `ANALYSIS_ENGINE_VERSION = v3`. The production topology is separate Render frontend/backend services, Neon PostgreSQL, GitHub API, optional Gemini, and a one-shot Alembic migration. The key engineering decision was treating AI as an interpretation capability rather than the authority for measurable analysis.

### Turkish Equivalent — Yaklaşık İki Dakika

DevLens’in çıkış noktası basit bir problemdi: GitHub portföylerinde faydalı mühendislik kanıtları bulunuyor, ancak bunları tutarlı biçimde incelemek zaman alıyor ve popularity metrikleri repository kalitesini açıklamıyor. Bu nedenle ürünü bir LLM’den developer değerlendirmesi istemek yerine deterministic bir çekirdek etrafında tasarladım.

Kullanıcı browser’da GitHub username giriyor. Next.js frontend isteği doğrudan FastAPI backend’e gönderiyor; backend username’i normalize edip doğruluyor. Önce PostgreSQL’de güncel analysis schema’sı ve engine version’ı ile uyumlu bir snapshot aranıyor. Cache miss durumunda public GitHub profile ve repository verileri alınıyor, fork ve archived repository’ler eleniyor ve seçilen repository’ler bounded concurrency ile analiz ediliyor.

Her repository için README, recursive tree ve seçili dependency manifest’leri inceleniyor. Documentation, testing, CI, hygiene, technology ve category sinyalleri çıkarılıyor. Repository score, portfolio aggregation, portfolio score, intelligence ve limitations deterministic olarak üretiliyor. Böylece ana sonuç tekrarlanabilir, kanıtla izlenebilir ve provider’dan bağımsız kalıyor.

Gemini bu sürecin sonrasında, ayrı bir interpretation katmanı olarak çalışıyor. Backend reduced structured context oluşturup yalnızca optional provider configured ise Gemini’ye gönderiyor. Gemini deterministic strength ve improvement alanlarını açıklayabilir ve grounded recommendation üretebilir; ancak evidence uyduramaz veya score değiştiremez. Schema ve signal-reference validation bu sınırı kontrol ediyor. Gemini kullanılamadığında stable unavailable sonucu dönüyor ve deterministic analysis korunuyor.

Snapshot’lar PostgreSQL JSONB içinde 900 saniyelik default TTL, `analysis_generated_at`, schema compatibility ve `ANALYSIS_ENGINE_VERSION = v3` ile tutuluyor. Production topology Render frontend/backend servisleri, Neon PostgreSQL, GitHub API, optional Gemini ve one-shot Alembic migration’dan oluşuyor. Temel teknik kararım, AI’ı ölçülebilir analysis’in otoritesi değil, interpretation capability olarak konumlandırmaktı.

## Likely Interview Questions

### 1. Why not use Gemini for scoring?

Scoring needs repeatability, inspectability, and evidence traceability. Deterministic rules make the core result easier to regression-test and keep it available independently of the AI provider.

### 2. Why PostgreSQL instead of Redis?

The product already needs durable analysis snapshots and their provenance metadata. PostgreSQL provides persistence and JSONB storage in one operational dependency; Redis was not needed for the current workload.

### 3. Why cache deterministic analysis?

The same public portfolio can require many GitHub requests. A fresh compatible snapshot reduces repeated provider work while TTL and version checks prevent stale or incompatible results from silently becoming authoritative.

### 4. Why use an analysis engine version?

Changing analysis logic can change the meaning of a snapshot even if its JSON schema remains valid. `ANALYSIS_ENGINE_VERSION` makes cache compatibility explicit; the current engine version is `v3`.

### 5. What happens if Gemini fails?

The interpretation result becomes a stable unavailable state with a reason such as timeout, rate limit, or invalid response. The deterministic analysis remains usable.

### 6. What happens if PostgreSQL fails?

Supported cache read failures fail open and supported persistence write failures are best-effort. The analysis path can continue without persistence where the current service behavior supports it. This is not a claim that every database or programmer error is swallowed.

### 7. Why bounded concurrency?

Portfolio analysis can trigger many GitHub calls. A semaphore limits concurrent repository work, controlling provider pressure and making resource use more predictable than unlimited fan-out.

### 8. What does partial success mean?

Handled repository-analysis failures can remain in the response as failure metadata while successful repositories still contribute evidence. Unexpected parser or programmer errors are not promised to be isolated universally.

### 9. How do you avoid exposing provider secrets?

GitHub, Gemini, and database credentials remain backend runtime configuration. The browser receives only public `NEXT_PUBLIC_API_BASE_URL` configuration, and secrets are excluded from structured logs.

### 10. What exactly does DevLens score?

It scores supported observable repository signals across Documentation, Testing & Automation, and Repository Hygiene. It does not score complete developer ability, employability, job fit, stars, forks, popularity, or technology choice.

### 11. What are the main limitations?

The system analyzes public GitHub evidence only, depends on external GitHub/Gemini availability, uses supported deterministic dimensions, and has time- and version-bounded cache reuse. It is not a hiring or ability assessment.

### 12. What would you improve next?

Potential future work includes richer deterministic signals, stronger parser resilience, improved provider failure isolation, comparison views, historical trends, broader test-evidence analysis, and stronger error correlation. These are not presented as current capabilities.

## Strong Technical Talking Points

- Deterministic scoring remains the authority for evidence, scores, findings, and limitations.
- Gemini is a constrained interpretation layer with schema and signal-reference validation.
- Evidence can be traced to observable README, tree, manifest, and engineering-practice signals.
- PostgreSQL snapshots use TTL, schema compatibility, and engine-version compatibility.
- Repository analysis uses bounded asynchronous concurrency for safer GitHub access.
- Supported provider failures degrade to partial or unavailable states without discarding valid deterministic output.
- Production migrations run as a separate one-shot Alembic operation.
- Structured request/provider/cache logs and privacy-conscious telemetry avoid raw prompts, payloads, secrets, and client tracking.

## GitHub Repository Metadata Audit

The current repository metadata was inspected read-only:

| Field | Current state |
| --- | --- |
| Visibility | Private |
| Description | Empty |
| Homepage | Empty |
| Topics | Empty |

No metadata was changed. Visibility was not changed.

### Recommended Repository Description

Deterministic GitHub portfolio analysis with explainable repository scoring and optional Gemini interpretation.

### Recommended Topics

```text
nextjs
fastapi
typescript
python
postgresql
github-api
gemini
portfolio-analysis
developer-tools
full-stack
```

### Recommended Homepage

`https://devlens-frontend-5hvj.onrender.com/`

This is the production frontend URL already documented in the repository. Metadata changes require a separate explicit action.

## Recruiter-Friendly Architecture Summary

Next.js / React / TypeScript frontend
→ FastAPI / Python backend
→ GitHub public evidence
→ deterministic repository and portfolio analysis
→ PostgreSQL snapshot cache
→ optional Gemini interpretation

Deterministic analysis owns scores and findings; Gemini only explains supplied context.

## Why This Project Matters

AI systems can blur the boundary between measurable logic and generated language. DevLens separates those responsibilities intentionally: evidence and scoring remain deterministic, while AI is constrained to explain the supplied result. That makes the core analysis more repeatable and keeps it useful when the AI provider is unavailable.

## Limitations Talking Points

When asked what DevLens cannot do:

- It analyzes public GitHub evidence, not private engineering work.
- It covers supported deterministic dimensions rather than complete developer ability.
- It does not predict employability, job fit, seniority, or hiring outcomes.
- It does not use stars, forks, or popularity as engineering-quality evidence.
- It depends on GitHub availability and optional Gemini availability.
- Free-tier deployment can introduce provider limits and wake-up latency.

## Future Improvements

The following are future work, not current capabilities:

1. Add richer deterministic repository signals while preserving evidence traceability.
2. Improve parser resilience for a broader range of dependency-file syntax.
3. Add stronger provider failure isolation and error correlation.
4. Add optional repository comparison and historical trend views.
5. Expand test-evidence analysis beyond the current supported structure signals.

## Links

- [Project README](../README.md)
- [Architecture](architecture.md)
- [Production Deployment](production-deployment.md)
- [Portfolio Case Study](case-study.md)
- [Live Demo](https://devlens-frontend-5hvj.onrender.com/)
