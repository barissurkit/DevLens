# Katkı Rehberi

Katkıda bulunmak istediğiniz için teşekkürler! Çalışma kuralları ve mimari ilkeler için [AGENTS.md](AGENTS.md) dosyasına da bakın (özellikle: skorları deterministik katman üretir, AI yalnızca yorumlar; arayüz metinleri Türkçedir; API secret'ları frontend'e yazılmaz).

## Kurulum

1. Repository'yi fork'layıp klonlayın ve `cp .env.example .env` ile yerel yapılandırmayı oluşturun (gerçek anahtarları commit etmeyin).
2. Backend (Python 3.12):

   ```bash
   cd backend
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

3. Frontend (Node.js 22):

   ```bash
   cd frontend
   npm ci
   ```

Docker Compose ile tüm yığını çalıştırmak için README'deki "Local Development" bölümüne bakın.

## Testleri çalıştırma

Backend:

```bash
cd backend
python -m pytest
```

Frontend:

```bash
cd frontend
npm run lint
npm run type-check
npm test
npm run build
```

PostgreSQL entegrasyon testleri ve tarayıcı (Playwright) testleri CI'da çalışır; ayrıntılar README'deki "Testing and CI" bölümündedir.

## Pull request beklentileri

- `main` dalı korumalıdır; ayrı bir dal açıp pull request gönderin.
- Pull request'i tek bir konuya odaklı tutun, gereksiz refactor yapmayın ve ne değiştiğini kısaca açıklayın.
- Davranış değiştiren her değişiklik için test ekleyin veya güncelleyin.
- Yukarıdaki kontroller yerelde geçmeli; `Required quality gates` CI kontrolü yeşil olmalıdır.
- `.env` dosyalarını, API anahtarlarını veya token'ları asla commit etmeyin.
