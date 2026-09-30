# DevLens çalışma kuralları

## Mimari

DevLens, frontend ve backend'i ayrı tutan iki parçalı bir web uygulamasıdır:

- **Frontend:** Next.js, TypeScript, App Router ve Tailwind CSS
- **Backend:** Python, FastAPI ve Pydantic
- Frontend ve backend kendi bağımlılıkları ve çalıştırma komutlarıyla ayrı yönetilir.

API secret'ları frontend koduna veya frontend environment değişkenlerine yazılmamalıdır. TypeScript'te gereksiz `any` kullanılmamalı, Python kodunda type hint tercih edilmelidir. Küçük ve anlaşılır component/fonksiyonlar kullanılmalıdır.

Yeni özellik eklenirken mevcut mimari korunmalı, kullanıcı açıkça istemedikçe kapsam büyütülmemeli ve yapılan görev dışında gereksiz refactor yapılmamalıdır. GitHub analizi, deterministik skorlama, isteğe bağlı AI yorumu, GitHub ile giriş ve çalışma alanı (geçmiş, aksiyon planı) özellikleri mevcuttur. Skorları ve bulguları deterministik katman üretir; AI yalnızca bunları yorumlar ve skorları değiştirmez. Bu ayrım korunmalıdır. Arayüz metinleri Türkçedir; kullanıcıya görünen yeni metinler de Türkçe yazılmalıdır.

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
npm test
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

PostgreSQL gerektiren testler `DEVLENS_TEST_DATABASE_URL` olmadan atlanır, ancak CI bu testlerin atlanmasına izin vermez. Yerelde çalıştırmak için `DATABASE_URL` ve `DEVLENS_TEST_DATABASE_URL` değerlerini aynı test veritabanına yönlendirip önce `alembic upgrade head` çalıştırın; ardından `tests/test_db_integration.py`, `tests/test_persistence_cache_final_postgres.py`, `tests/test_snapshot_public_postgres.py`, `tests/test_session_cleanup.py` ve `tests/test_action_plan_postgres.py` dosyalarını çalıştırın.
