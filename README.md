# DevLens

DevLens, ileride public GitHub profillerini ve repository'lerini analiz ederek geliştirici portföyleri hakkında içgörüler sunmayı hedefleyen bir Developer Portfolio Intelligence uygulamasıdır.

## Mevcut aşama

Bu ilk aşamada yalnızca temel proje mimarisi kurulmuştur:

- Next.js + TypeScript + App Router + Tailwind CSS frontend iskeleti
- FastAPI + Pydantic backend iskeleti
- Backend'de temel `GET /health` endpoint'i

GitHub API entegrasyonu, AI/Gemini, veritabanı, dashboard ve scoring sistemi henüz eklenmemiştir.

## Teknoloji stack'i

- **Frontend:** Next.js, TypeScript, Tailwind CSS
- **Backend:** Python, FastAPI, Pydantic, Uvicorn

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
