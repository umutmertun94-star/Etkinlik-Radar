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
- **Arama keşfi**: sabit havuzun *dışındaki* etkinlikleri haftalık sorgularla yakalar — `BRAVE_API_KEY` tanımlıysa Brave Search API, değilse anahtarsız DuckDuckGo
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

## Ortam değişkenleri (hepsi opsiyonel)

Hiçbiri tanımlı olmasa da sistem çalışır; her biri bir katmanı iyileştirir.
Actions'ta: repo → Settings → Secrets and variables → Actions.

| Değişken | Ne yapar | Tanımlı değilse |
|---|---|---|
| `ANTHROPIC_API_KEY` | Keşif ipuçlarını ilgililik puanına göre eler, tarih/format çıkarır | Filtre atlanır, tüm ipuçları bültene düşer |
| `ANTHROPIC_MODEL` | Kullanılacak model (repo *variable*'ı) | `claude-haiku-4-5-20251001` |
| `BRAVE_API_KEY` | Keşif sorguları Brave Search API'sine gider | Anahtarsız DuckDuckGo'ya düşülür |

### Brave Search API notu

`sources.yaml`'daki keşif sorguları anahtar varken Brave'e, yokken DDG'ye
gider — sorgu listesi, kategoriler ve `max` değerleri ikisinde de aynıdır
(`max` → Brave'in `count` parametresi). Sonuçlar son 1 yılla sınırlanır
(`freshness=py`).

- **Hacim**: ~40 sorgu × haftada 1 tarama ≈ **aylık 180 sorgu**. Ücretsiz
  katmanın aylık kotasının ve 5 $'lık aylık kredinin epey altında; yine de
  sorgu listesi büyütülürse bu hesabı güncelleyin. Kota aşılırsa istekler
  hata döner, kaynak sessizce boş geçer — sistem kırılmaz, ama o hafta
  keşif katmanı çalışmaz. Kritikse Brave panelinden kullanım uyarısı kurun.
- **Hız sınırı**: ücretsiz katman 1 sorgu/saniye. Fetcher sorgular arasında
  1,1 sn bekler; ~40 sorgu ≈ 45 saniye sürer.
- **Atıf şartı**: ücretsiz katman, sonuçların gösterildiği yerde Brave'e
  atıf ister. Dashboard footer'ında "Search powered by Brave" bağlantısı
  bunun için duruyor — Brave kullanılıyorsa **kaldırmayın**.

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

## Bilinen kaynak kısıtları

### Gartner webinarları — Cloudflare challenge (kapalı)

`gartner-webinars` kaynağı `enabled: false` bırakıldı. Sebebi "sayfa JS ile
yükleniyor" değil; hub'ın arkasındaki JSON ucu bulundu ama sunucudan
çekilemiyor:

```
https://www.gartner.com/ngw/syspath-bin/gartner/dynamiccontent
  ?requestType=select-webinars-by-session-type-tags&designType=webinar
  &start=0&pageSize=50&languageCode=en
  &tags=emt%3Apage%2Fcontent-type%2Fwebinar
  &webinarType=all-webinars&webinarSource=all-webinars
```

Yanıt şeması aradığımız her alanı içeriyor:
`data.upcomingWebinars[]` → `title`, `url` (`/en/webinar/<event_id>/<session_id>-slug`),
`allFields.publishdate` (ISO 8601, UTC), `allFields.webinar_startepoch`,
`allFields.webinar_durationtext`, `tags`.

Engel: **gartner.com'un tamamı Cloudflare bot korumasının arkasında.**
`robots.txt` dahil her yol düz bir HTTP istemcisine `403` dönüyor
(`server: cloudflare`, `cf-mitigated: challenge`). User-Agent, Referer ve
Accept-Language taklidi durumu değiştirmiyor — istenen şey tarayıcıda
çalışan bir JS challenge yanıtı. Tarayıcıda açıldığında uç nokta `200`
dönüyor, `requests` ile hiçbir başlık kombinasyonunda dönmüyor.

Sonuç: GitHub Actions'ta çalışan `requests` tabanlı bir fetcher bu kaynağı
çekemez. Challenge'ı aşmaya çalışmak (headless tarayıcı, challenge çözücü
servis) hem kırılgan hem de Gartner kullanım şartlarına aykırı; bu yüzden
yapılmadı. Kaynak açılmak istenirse gereken şey ayrı bir tarayıcı
otomasyonu adımıdır (Playwright + Actions'ta ek servis) — mevcut mimarinin
"sunucu yok, bağımlılık az" tercihiyle çelişir.

O zamana kadar Gartner'ı `sources.yaml`'daki iki DDG sorgusu taşıyor
(`site:gartner.com webinar AI security 2026 register` ve
`complimentary Gartner webinar AI governance`); bunlar bilinçli olarak
yerinde bırakıldı.

## Faz 2 fikirleri (mimari hazır)

- LLM filtreleme (hazır): Anthropic API anahtarını secrets'a ekleyin — haber-radar ile aynı anahtar
- İpuçlarından otomatik tarih/yer çıkarımı (LLM ile)
- E-posta bildirimi (Actions üzerinden ücretsiz eklenebilir)
- Bülteni mevcut bülten üretici araca besleme (docs/events.json hazır)
