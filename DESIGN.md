# DESIGN.md

## Mimari ve Trade-off Açıklamaları

- FastAPI tabanlı reverse proxy
- Modüler filtre yapısı
- Observability için Prometheus ve structured logging
- Trade-off: Hız vs. Güvenlik, Basitlik vs. Esneklik

## Konfigürasyon ve Sırlar

- `GEMINI_API_KEY` `.env` üzerinden yüklenir (`python-dotenv`).
- Anahtar yoksa LLM çağrıları devre dışı kalır ve anlaşılır hata döner.
- Trade-off: Basit `.env` yönetimi vs. üretimde gizli yönetimi (Vault/Secret Manager).

## Injection Detection

- Heuristic anahtar kelime kontrolü ile hızlı tespit.
- Dummy binary classifier ile modüler yapı (gerekirse gerçek model entegre edilebilir).
- Trade-off: Hızlı tespit için anahtar kelime, daha iyi doğruluk için model.

## Rate-limit & LRU Cache

- Kullanıcı başına saniyelik rate-limit.
- Aynı istek 5 dakika içinde gelirse cache'den dönüyor.
- Trade-off: Düşük latency için cache, adil kullanım için rate-limit.

## Giriş Toksisite Filtresi (Early Block)

- `gateway/main.py` içinde girişte toksisite kontrolü; toksik istekler LLM çağrılmadan engellenir.
- Trade-off: Daha az false negative için hassasiyet artırımı vs. false positive riski ve kullanıcı deneyimi.

## PII Doğrulama (Regex + Hafif Öğrenen Katman)

- Obfuscation/spacing normalizasyonu: `[at]/[dot]`, boşluklu IBAN/telefon varyantları.
- Genişletilmiş regex seti + basit skorlu yaklaşım (lightweight ML-like).
- Trade-off: Ek kurallar = daha yüksek recall; küçük ek işlem maliyeti.

## Opsiyonel LLM‑Judge (Toxicity)

- Ortam değişkeni `TOXICITY_JUDGE=true` ise, heuristik sonrası ek bir LLM değerlendirmesi yapılır.
- Tek amaç: borderline durumlarda ikinci görüş; JSON `{toxic, score}` beklenir.
- Trade-off: Ek token maliyeti ve gecikme vs. daha düşük FN olasılığı.
