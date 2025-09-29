# CASE 1 — LLM Gateway (Guardrails + Observability)

FastAPI tabanlı bir LLM gateway: giriş/çıkış guardrail filtreleri, gözlemlenebilirlik (Prometheus metrikleri), kimlik doğrulama ve değerlendirme araçları ile birlikte gelir.

## Özellikler

- Pre‑filters (giriş): PII redaksiyon (email, telefon, IBAN + obfuscation), prompt‑injection tespiti (anahtar kelime + regex + bağlam + skor), rate‑limit (kullanıcı başına), LRU cache (5 dk)
- Post‑filters (çıktı): Toksisite/policy ihlali tespiti (şiddet skoru), şema zorlaması (otomatik düzeltme)
- Observability: `/metrics` (Prometheus), histogram ve sayaç metrikleri, istek başına structured log ile filtre izleri
- Auth: HTTP Bearer token, izin tabanlı kontrol
- Değerlendirme: `attack_set.json` ile precision/recall, grafik üretimi

---

## Hızlı Başlangıç

### Gereksinimler

- Python 3.10+ (Windows/macOS/Linux)
- Pip

### Kurulum (Windows PowerShell)

```powershell
git clone <REPO_URL> case-1
cd case-1
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Ortam değişkenleri için .env oluşturun (opsiyonel)
@"
GEMINI_API_KEY=
TOXICITY_JUDGE=false
"@ | Out-File -Encoding UTF8 .env
```

### Kurulum (macOS/Linux)

```bash
git clone <REPO_URL> case-1
cd case-1
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cat > .env << 'EOF'
GEMINI_API_KEY=
TOXICITY_JUDGE=false
EOF
```

> Not: `GEMINI_API_KEY` set edilmezse LLM çağrıları devre dışı kalır; gateway hatasız çalışır, testler geçer.

---

## Uygulamayı Çalıştırma

```powershell
uvicorn gateway.main:app --host 0.0.0.0 --port 8000 --reload
```

- Swagger/OpenAPI: `http://localhost:8000/docs`
- Redoc: `http://localhost:8000/redoc`

Prod önerisi (örnek):

```bash
uvicorn gateway.main:app --host 0.0.0.0 --port 8000 --workers 2
```

---

## Kimlik Doğrulama (Auth)

### Token Oluşturma

```powershell
$resp = Invoke-RestMethod -Uri http://localhost:8000/auth/token -Method Post -ContentType 'application/json' -Body '{"user_id":"demo","permissions":["chat","metrics"]}'
$token = $resp.token
"Bearer $token"
```

### Token ile Çağrı

```powershell
Invoke-RestMethod -Uri http://localhost:8000/chat -Method Post -ContentType 'application/json' -Headers @{Authorization="Bearer $token"} -Body '{"input":"Merhaba!"}'
```

> İzinler: `chat`, `metrics` (örnek). `auth.py` içinde basit in‑memory saklama vardır.

---

## Uç Noktalar

### POST /chat

Seçilen LLM’ye proxy eder, aşağıdaki sırayla guardrails uygular:

1. Rate‑limit (kullanıcı başı 10/dk)
2. PII redaksiyon (email, tel, IBAN; obfuscation/boşluk varyantları)
3. Prompt‑injection tespiti (anahtar kelime + regex + bağlam + skor)
4. Giriş toksisite engelleme (erken bloklama)
5. LRU cache (5 dk)
6. LLM çağrısı (GEMINI_API_KEY varsa)
7. Çıkış toksisite kontrolü (+ opsiyonel LLM‑judge `TOXICITY_JUDGE=true`)
8. Şema zorlaması (yanıtı `{"output": str, "cache": bool}` hale getirir)

Örnek yanıt:

```json
{ "output": "Merhaba! Size nasıl yardımcı olabilirim?", "cache": false }
```

### GET /metrics

Prometheus uyumlu metrikler döner. Örnek metrikler:

- `chat_requests_total`
- `chat_requests_blocked_total`
- `chat_cache_hit_total`
- `chat_latency_seconds` (Histogram)
- `llm_errors_total`, `llm_tokens_total`, `auth_errors_total`

Prometheus scrape örneği:

```yaml
scrape_configs:
  - job_name: "llm-gateway"
    static_configs:
      - targets: ["localhost:8000"]
    metrics_path: /metrics
```

### GET /health

Gateway/LLM sağlık durumu ve zaman damgası.

### GET /stats

Cache boyutu/kapasitesi ve LLM kullanım istatistikleri.

### Auth ile ilgili uç noktalar

- `POST /auth/token` → Token üretimi
- `GET /auth/user/{user_id}` → Kullanıcı istatistikleri (admin izni gerektirir)
- `GET /auth/system` → Sistem istatistikleri (admin izni gerektirir)
- `DELETE /auth/token` → Mevcut token’ı iptal etme

---

## Testler ve Değerlendirme

### Testleri Çalıştırma

```powershell
pytest -q
```

Beklenen: `14 passed`

### Saldırı Seti Değerlendirmesi

```powershell
python eval_attack_set.py
```

Örnek çıktı (özet):

```json
{
  "macro_precision": 1.0,
  "macro_recall": 0.933,
  "normal_fp_total": 0
}
```

### Grafikleri Üretme

```powershell
python generate_charts.py
```

Üretilen dosyalar: `charts/precision_recall.png`, `charts/latency.png`

---

## Konfigürasyon ve Ayarlar

- `.env`

  - `GEMINI_API_KEY`: Gemini API anahtarı (opsiyonel)
  - `TOXICITY_JUDGE`: `true/false` → Yargıç katmanı (ek toksisite kontrolü)

- `filters/rate_limit.py`:

  - `RATE_LIMIT_WINDOW=60`, `RATE_LIMIT_MAX=10`

- `filters/cache.py`:

  - LRU kapasitesi (varsayılan 100), TTL ≈ 300 sn

- `filters/schema.py`:
  - Yanıt şeması: `{"output": str, "cache": bool}`

---

## Proje Yapısı

```
gateway/           FastAPI uygulaması
filters/           Guardrail filtreleri (pii, injection, toxicity, cache, rate_limit, schema)
tests/             Pytest testleri
attack_set.json    Etiketli saldırı seti
eval_attack_set.py Precision/Recall değerlendirme scripti
generate_charts.py Grafik üretimi (precision/recall, latency)
DESIGN.md          Mimari ve trade‑off’lar
EXPERIMENTS.md     Deney günlüğü
PROMPTS.md         Kullanılan promptlar
REPORT.md          Ölçümler ve görseller
```

---
