# DevLens çalışma kuralları

## Mimari

DevLens, frontend ve backend'i ayrı tutan iki parçalı bir web uygulamasıdır:

- **Frontend:** Next.js, TypeScript, App Router ve Tailwind CSS
- **Backend:** Python, FastAPI ve Pydantic
- Frontend ve backend kendi bağımlılıkları ve çalıştırma komutlarıyla ayrı yönetilir.

API secret'ları frontend koduna veya frontend environment değişkenlerine yazılmamalıdır. TypeScript'te gereksiz `any` kullanılmamalı, Python kodunda type hint tercih edilmelidir. Küçük ve anlaşılır component/fonksiyonlar kullanılmalıdır.

Yeni özellik eklenirken mevcut mimari korunmalı, kullanıcı açıkça istemedikçe kapsam büyütülmemeli ve yapılan görev dışında gereksiz refactor yapılmamalıdır. GitHub analiz ve AI özellikleri sonraki aşamalarda eklenecektir.

## Geliştirme komutları

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Frontend kontrolleri:

```bash
npm run lint
npm run type-check
npm run build
```

Backend:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Backend testleri:

```bash
pytest
```
