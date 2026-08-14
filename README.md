# Etkinlik Radarı

Merkez bankasını ilgilendiren teknoloji etkinliklerini (yapay zeka, siber güvenlik, kuantum, veri merkezi, AI governance, ödeme sistemleri, genel BT) her hafta otomatik tarayan, bülten ve dashboard üreten sistem. Faz 1: tamamen ücretsiz — sunucu yok, API anahtarı yok.

## Nasıl çalışır

```
sources.yaml ──► radar/fetchers.py ──► tekilleştirme (store.py)
                                            │
                              ┌─────────────┴─────────────┐
                     output/bulten-YYYY-HXX.md      docs/index.html
                     (haftalık bülten)              (GitHub Pages dashboard)
```

- **confs.tech**: açık konferans veritabanı, kutudan çıktığı gibi çalışır
- **DuckDuckGo keşfi**: sabit havuzun *dışındaki* etkinlikleri haftalık sorgularla yakalar
- **Google Alerts (RSS)**: pasif keşif — kurulunca kendiliğinden akar
- **HTML kaynakları**: BIS, SUERF, OMFIF, kommunity, SANS vb. — her biri için CSS seçicisi ayarlanır

Her tarama yalnızca **ilk kez görülen** etkinlikleri bültene yazar; dashboard ise tüm doğrulanmış yaklaşan etkinlikleri gösterir. Arama/alerts kaynaklı bulgular "doğrulanacak ipuçları" bölümüne düşer (tarih/format elle teyit edilir, iyi çıkanlar kaynak havuzuna eklenir).

## Kurulum (bir kere, ~15 dakika)

1. **Repo**: GitHub'da yeni repo aç (private olabilir), bu dosyaları push'la.
2. **Actions**: repo → Settings → Actions → "Allow all actions" açık olsun.
   Workflow her pazartesi 09:00 TSİ'de kendiliğinden çalışır; Actions
   sekmesinden "Run workflow" ile elle de tetiklenir.
3. **Pages (dashboard)**: Settings → Pages → Source: "Deploy from a branch"
   → Branch: `main`, klasör: `/docs`. Dashboard adresi:
   `https://<kullanici>.github.io/<repo>/`
4. **Google Alerts** (opsiyonel ama önerilir): google.com/alerts →
   sorgu oluştur → Teslim: **RSS özet akışı** → feed linkini `sources.yaml`'daki
   ilgili kaynağa yapıştır, `enabled: true` yap. Önerilen sorgular:
   - `"yapay zeka" (konferans OR zirve OR webinar) 2026`
   - `(quantum OR post-quantum) cryptography (conference OR webinar)`
   - `"AI governance" (summit OR webinar OR conference)`
   - `CBDC OR "central bank digital currency" conference`
   - `"veri merkezi" (zirve OR konferans OR etkinlik)`

## Lokal çalıştırma

```bash
pip install -r requirements.txt
python -m radar.run                      # tüm etkin kaynaklar
python -m radar.run --only confstech     # tek kaynak testi
```

## Kaynak eklemek

`sources.yaml`'a yeni blok ekleyin — kod değişikliği gerekmez.
HTML kaynakları için sayfanın yapısına uygun CSS seçicileri gerekir
(`selectors: {item, title, link, date}`). Seçici ayarlanana kadar
`enabled: false` bırakın.

## Faz 2 fikirleri (mimari hazır)

- LLM filtreleme (hazır): Anthropic API anahtarını secrets'a ekleyin — haber-radar ile aynı anahtar
- İpuçlarından otomatik tarih/yer çıkarımı (LLM ile)
- E-posta bildirimi (Actions üzerinden ücretsiz eklenebilir)
- Bülteni mevcut bülten üretici araca besleme (docs/events.json hazır)
