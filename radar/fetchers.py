"""Kaynak türlerine göre etkinlik çekiciler.

Her fetcher sources.yaml'daki bir kaynak tanımını alır ve Event listesi döner.
Yeni kaynak türü eklemek = buraya bir fonksiyon + FETCHERS sözlüğüne kayıt.
"""
from __future__ import annotations

import datetime as dt
import json
import re

import requests
from bs4 import BeautifulSoup

from .models import Event

UA = {"User-Agent": "etkinlik-radar/0.1 (+https://github.com/)"}
TIMEOUT = 30


def _get(url: str) -> requests.Response:
    r = requests.get(url, headers=UA, timeout=TIMEOUT)
    r.raise_for_status()
    return r


# ---------------------------------------------------------------- confs.tech
CONFSTECH_RAW = (
    "https://raw.githubusercontent.com/tech-conferences/"
    "conference-data/main/conferences/{year}/{topic}.json"
)


def fetch_confstech(src: dict) -> list[Event]:
    """confs.tech açık veritabanı (GitHub'daki JSON dosyaları)."""
    events: list[Event] = []
    year = dt.date.today().year
    for y in (year, year + 1):
        for topic in src.get("topics", []):
            try:
                data = _get(CONFSTECH_RAW.format(year=y, topic=topic)).json()
            except Exception:
                continue  # o yıl/konu dosyası henüz yoksa sorun değil
            for item in data:
                events.append(Event(
                    title=item.get("name", "").strip(),
                    url=item.get("url", ""),
                    category=src.get("category_map", {}).get(topic, src["category"]),
                    source=src["id"],
                    start_date=item.get("startDate"),
                    end_date=item.get("endDate"),
                    city=item.get("city"),
                    country=item.get("country"),
                    online=bool(item.get("online")) if "online" in item else None,
                ))
    return events


# --------------------------------------------------------------------- RSS
def fetch_rss(src: dict) -> list[Event]:
    """RSS/Atom kaynakları — Google Alerts dahil.

    Alerts girdileri etkinliğin kendisi değil 'ipucu'dur: tarih alanı boş
    bırakılır ve needs_review=True işaretlenir; bültende ayrı bölümde çıkar.
    """
    import feedparser

    feed = feedparser.parse(src["url"])
    events: list[Event] = []
    for e in feed.entries[: src.get("limit", 25)]:
        title = re.sub(r"<[^>]+>", "", getattr(e, "title", "")).strip()
        link = getattr(e, "link", "")
        if not title or not link:
            continue
        events.append(Event(
            title=title,
            url=link,
            category=src["category"],
            source=src["id"],
            needs_review=src.get("needs_review", True),
        ))
    return events


# -------------------------------------------------------- genel HTML kazıma
def fetch_html(src: dict) -> list[Event]:
    """Konfigürasyonla yönetilen genel HTML kazıyıcı.

    sources.yaml'da her kaynak için CSS seçicileri tanımlanır:
      selectors:
        item: ".event-card"
        title: "h3"
        link: "a"          # href alınır
        date: ".date"      # opsiyonel, ham metin olarak saklanır
    """
    sel = src["selectors"]
    soup = BeautifulSoup(_get(src["url"]).text, "html.parser")
    events: list[Event] = []
    for node in soup.select(sel["item"])[: src.get("limit", 40)]:
        t = node.select_one(sel["title"])
        a = node.select_one(sel.get("link", "a"))
        if not t or not a or not a.get("href"):
            continue
        url = requests.compat.urljoin(src["url"], a["href"])
        date_raw = None
        if sel.get("date"):
            d = node.select_one(sel["date"])
            date_raw = d.get_text(" ", strip=True) if d else None
        events.append(Event(
            title=t.get_text(" ", strip=True),
            url=url,
            category=src["category"],
            source=src["id"],
            needs_review=True,
            extra={"date_raw": date_raw} if date_raw else {},
        ))
    return events


# ------------------------------------------------------- DuckDuckGo keşfi
def fetch_ddg(src: dict) -> list[Event]:
    """Anahtar gerektirmeyen arama keşfi (ddgs kütüphanesi).

    Sabit havuzun dışındaki etkinlikleri yakalamak için haftalık sorgular.
    Sonuçlar 'ipucu' niteliğindedir: needs_review=True.
    """
    try:
        from ddgs import DDGS
    except ImportError:
        try:
            from duckduckgo_search import DDGS  # eski paket adı
        except ImportError:
            print(f"[{src['id']}] ddgs kurulu değil, atlanıyor")
            return []

    events: list[Event] = []
    with DDGS() as ddgs:
        for q in src.get("queries", []):
            try:
                results = list(ddgs.text(q["q"], max_results=q.get("max", 8)))
            except Exception as ex:
                print(f"[{src['id']}] sorgu hatası ({q['q']}): {ex}")
                continue
            for r in results:
                events.append(Event(
                    title=r.get("title", "").strip(),
                    url=r.get("href", ""),
                    category=q.get("category", src.get("category", "genel-bt")),
                    source=src["id"],
                    needs_review=True,
                    extra={"query": q["q"], "snippet": r.get("body", "")[:200]},
                ))
    return events


# ------------------------------------------------- çekirdek (elle) liste
def _nth_weekday(year: int, month: int, weekday: int, n: int) -> dt.date:
    """Ayın n. haftaiçi günü (weekday: 0=Pzt ... 6=Paz)."""
    d = dt.date(year, month, 1)
    return d + dt.timedelta(days=(weekday - d.weekday()) % 7 + 7 * (n - 1))


def fetch_manual(src: dict) -> list[Event]:
    """sources.yaml içinde elle tutulan çapa etkinlikler (GITEX, MWC vb.).

    Kaçırılması kabul edilemez büyük etkinlikler keşif katmanına
    bırakılmaz; bu listede durur ve dashboard/bültene doğrudan girer.

    Tekrarlayan seriler (ör. TRAI Meet-Up: her ayın 3. çarşambası) için
    tarih yerine recurring alanı verilir; gelecek tarihler hesaplanır:
      recurring: {weekday: 2, ordinal: 3, months_ahead: 3}
    """
    events: list[Event] = []
    today = dt.date.today()
    for item in src.get("events", []):
        rec = item.get("recurring")
        if rec:
            y, m = today.year, today.month
            for _ in range(rec.get("months_ahead", 3) + 1):
                d = _nth_weekday(y, m, rec.get("weekday", 2), rec.get("ordinal", 3))
                if d >= today:
                    events.append(Event(
                        title=item["title"], url=item["url"],
                        category=item.get("category", "genel-bt"),
                        source=src["id"], start_date=d.isoformat(),
                        city=item.get("city"), country=item.get("country"),
                        online=item.get("online"),
                    ))
                m += 1
                if m > 12:
                    m, y = 1, y + 1
            continue
        events.append(Event(
            title=item["title"],
            url=item["url"],
            category=item.get("category", "genel-bt"),
            source=src["id"],
            start_date=item.get("start_date"),
            end_date=item.get("end_date"),
            city=item.get("city"),
            country=item.get("country"),
            online=item.get("online"),
        ))
    return events


# ------------------------------------------------------------ kommunity
def fetch_kommunity(src: dict) -> list[Event]:
    """kommunity.com toplulukları (TRAI vb. Türkiye teknoloji meetupları).

    Sitenin kendi API ucunu kullanır; şema değişirse loglardan görülür,
    alanlar savunmacı okunur.
    """
    events: list[Event] = []
    for slug in src.get("communities", []):
        url = f"https://api.kommunity.com/api/v1/{slug}/events?page=1"
        try:
            data = _get(url).json()
        except Exception as ex:
            print(f"[{src['id']}] {slug}: erişilemedi ({ex})")
            continue
        items = data.get("data") or data.get("events") or []
        if not items:
            print(f"[{src['id']}] {slug}: kayıt gelmedi (şema kontrolü gerekebilir)")
        for it in items:
            title = it.get("name") or it.get("title") or ""
            eslug = it.get("slug") or ""
            eurl = it.get("detail_url") or (
                f"https://kommunity.com/{slug}/events/{eslug}" if eslug else "")
            sd = it.get("start_date")
            if isinstance(sd, dict):
                sd = sd.get("date") or sd.get("iso") or None
            if isinstance(sd, str):
                sd = sd[:10]
            venue = (it.get("venue") or {}) if isinstance(it.get("venue"), dict) else {}
            online = it.get("is_online")
            events.append(Event(
                title=title, url=eurl,
                category=src.get("category", "genel-bt"),
                source=src["id"],
                start_date=sd,
                city=venue.get("city") or "İstanbul/Ankara?",
                country="Türkiye",
                online=bool(online) if online is not None else None,
                needs_review=sd is None,
            ))
    return events


# ------------------------------------------------------------------ Techmeme
TECHMEME_URL = "https://www.techmeme.com/events"

# Satır başındaki bilgi etiketleri — etkinliğin adının parçası değil.
# VIRTUAL/HYBRID <em> içinde gelir, NEW DATES düz metin olarak.
TECHMEME_MARKERS = ("VIRTUAL:", "HYBRID:", "NEW DATES:")

# Etkinlik olmayan satırlar (bilanço takvimi aynı listede yayımlanıyor).
TECHMEME_SKIP = re.compile(r"^(earnings|dividends?)\s*:", re.I)

_MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun",
     "jul", "aug", "sep", "oct", "nov", "dec"], 1)}

# "Austin, TX" gibi ABD eyalet kısaltmaları → United States
_US_STATES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "DC", "FL", "GA", "HI",
    "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD", "MA", "MI", "MN",
    "MS", "MO", "MT", "NE", "NV", "NH", "NJ", "NM", "NY", "NC", "ND", "OH",
    "OK", "OR", "PA", "RI", "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA",
    "WV", "WI", "WY", "PR",
}

# Techmeme şehir hücresinde çoğu zaman ülke yazmaz ("Seoul", "London").
# Sabit eşleme listesi: listede olmayan şehirde country BOŞ bırakılır —
# yuz_yuze_ulkeler kuralı ülkesi bilinmeyen yüz yüze etkinliği zaten eler,
# yani bilinmeyen şehir temkinli tarafa düşer.
TECHMEME_CITY_COUNTRY = {
    # Türkiye
    "istanbul": "Türkiye", "ankara": "Türkiye", "izmir": "Türkiye",
    "antalya": "Türkiye",
    # ABD (eyaletsiz yazılan büyük şehirler)
    "las vegas": "United States", "san francisco": "United States",
    "new york": "United States", "los angeles": "United States",
    "san diego": "United States", "san jose": "United States",
    "seattle": "United States", "boston": "United States",
    "chicago": "United States", "austin": "United States",
    "atlanta": "United States", "denver": "United States",
    "dallas": "United States", "houston": "United States",
    "detroit": "United States", "orlando": "United States",
    "miami": "United States", "miami beach": "United States",
    "phoenix": "United States", "portland": "United States",
    "philadelphia": "United States", "nashville": "United States",
    "minneapolis": "United States", "new orleans": "United States",
    "salt lake city": "United States", "kansas city": "United States",
    "palo alto": "United States", "santa clara": "United States",
    "mountain view": "United States", "menlo park": "United States",
    "sunnyvale": "United States", "cupertino": "United States",
    "napa valley": "United States", "maui": "United States",
    "honolulu": "United States", "anaheim": "United States",
    # Kanada
    "toronto": "Canada", "montreal": "Canada", "vancouver": "Canada",
    "ottawa": "Canada", "calgary": "Canada", "edmonton": "Canada",
    "waterloo": "Canada",
    # Birleşik Krallık / İrlanda
    "london": "United Kingdom", "edinburgh": "United Kingdom",
    "manchester": "United Kingdom", "glasgow": "United Kingdom",
    "bristol": "United Kingdom", "leeds": "United Kingdom",
    "dublin": "Ireland",
    # Avrupa
    "amsterdam": "Netherlands", "rotterdam": "Netherlands",
    "eindhoven": "Netherlands", "the hague": "Netherlands",
    "berlin": "Germany", "munich": "Germany", "cologne": "Germany",
    "hamburg": "Germany", "frankfurt": "Germany", "nuremberg": "Germany",
    "stuttgart": "Germany", "dusseldorf": "Germany",
    "paris": "France", "cannes": "France", "nice": "France",
    "lyon": "France", "toulouse": "France",
    "barcelona": "Spain", "madrid": "Spain", "valencia": "Spain",
    "malaga": "Spain", "bilbao": "Spain",
    "rome": "Italy", "milan": "Italy", "turin": "Italy",
    "florence": "Italy", "venice": "Italy",
    "lisbon": "Portugal", "porto": "Portugal",
    "zurich": "Switzerland", "geneva": "Switzerland", "basel": "Switzerland",
    "davos": "Switzerland", "lugano": "Switzerland",
    "vienna": "Austria", "salzburg": "Austria",
    "brussels": "Belgium", "antwerp": "Belgium",
    "copenhagen": "Denmark", "stockholm": "Sweden",
    "gothenburg": "Sweden", "oslo": "Norway", "helsinki": "Finland",
    "reykjavik": "Iceland", "tallinn": "Estonia", "riga": "Latvia",
    "vilnius": "Lithuania", "warsaw": "Poland", "krakow": "Poland",
    "prague": "Czechia", "budapest": "Hungary", "bucharest": "Romania",
    "sofia": "Bulgaria", "athens": "Greece", "belgrade": "Serbia",
    "zagreb": "Croatia", "ljubljana": "Slovenia",
    # Orta Doğu / Afrika
    "dubai": "United Arab Emirates", "abu dhabi": "United Arab Emirates",
    "riyadh": "Saudi Arabia", "jeddah": "Saudi Arabia", "neom": "Saudi Arabia",
    "doha": "Qatar", "manama": "Bahrain", "kuwait city": "Kuwait",
    "muscat": "Oman", "tel aviv": "Israel", "jerusalem": "Israel",
    "cairo": "Egypt", "marrakech": "Morocco", "casablanca": "Morocco",
    "cape town": "South Africa", "johannesburg": "South Africa",
    "nairobi": "Kenya", "lagos": "Nigeria",
    # Asya / Pasifik
    "seoul": "South Korea", "busan": "South Korea", "incheon": "South Korea",
    "tokyo": "Japan", "osaka": "Japan", "kyoto": "Japan",
    "yokohama": "Japan", "beijing": "China", "shanghai": "China",
    "shenzhen": "China", "guangzhou": "China", "hangzhou": "China",
    "wuzhen": "China", "hong kong": "Hong Kong", "taipei": "Taiwan",
    "singapore": "Singapore", "kuala lumpur": "Malaysia",
    "jakarta": "Indonesia", "bali": "Indonesia", "bangkok": "Thailand",
    "hanoi": "Vietnam", "ho chi minh city": "Vietnam", "manila": "Philippines",
    "bengaluru": "India", "bangalore": "India", "mumbai": "India",
    "new delhi": "India", "delhi": "India", "hyderabad": "India",
    "chennai": "India", "pune": "India", "goa": "India",
    "sydney": "Australia", "melbourne": "Australia", "brisbane": "Australia",
    "perth": "Australia", "adelaide": "Australia", "canberra": "Australia",
    "gold coast": "Australia", "auckland": "New Zealand",
    "wellington": "New Zealand",
    # Latin Amerika
    "mexico city": "Mexico", "guadalajara": "Mexico", "monterrey": "Mexico",
    "cancun": "Mexico", "sao paulo": "Brazil", "rio de janeiro": "Brazil",
    "buenos aires": "Argentina", "santiago": "Chile", "bogota": "Colombia",
    "medellin": "Colombia", "lima": "Peru",
}


def _techmeme_dates(raw: str, year: int) -> tuple[str | None, str | None, int | None]:
    """'Aug 30-Sep 7' -> ('YYYY-08-30', 'YYYY-09-07', 8).

    Sayfada yıl yazmaz; başlangıç ayını da döner ki çağıran taraf ay geriye
    sardığında (Ara -> Oca) yılı ilerletebilsin.
    """
    m = re.match(
        r"([A-Za-z]{3})[a-z]*\s+(\d{1,2})"
        r"(?:\s*[-–—]\s*(?:([A-Za-z]{3})[a-z]*\s+)?(\d{1,2}))?",
        (raw or "").strip(),
    )
    if not m:
        return None, None, None
    smon = _MONTHS.get(m.group(1).lower())
    if not smon:
        return None, None, None
    emon = _MONTHS.get((m.group(3) or "").lower()) or smon
    try:
        start = dt.date(year, smon, int(m.group(2)))
        end = dt.date(year + (1 if emon < smon else 0), emon,
                      int(m.group(4)) if m.group(4) else int(m.group(2)))
    except ValueError:                      # sayfadaki hatalı gün (ör. Feb 30)
        return None, None, smon
    return start.isoformat(), end.isoformat(), smon


def _techmeme_place(loc_raw: str, marker: str) -> tuple[str | None, str | None, bool | None]:
    """Şehir hücresi + satır etiketinden (city, country, online) üretir."""
    if marker.startswith("VIRTUAL"):
        return None, None, True             # tamamen çevrimiçi: yer bilgisi yok
    # HYBRID'de uzaktan katılım mümkün -> online sayılır, yer bilgisi korunur.
    online = True if marker.startswith("HYBRID") else (False if loc_raw else None)
    if not loc_raw:
        return None, None, online
    city, _, tail = loc_raw.partition(",")
    city, tail = city.strip(), tail.strip()
    if tail:                                # "Austin, TX" / "Bali, Indonesia"
        country = "United States" if tail.upper() in _US_STATES else tail
    else:
        country = TECHMEME_CITY_COUNTRY.get(city.lower())
    return city or None, country, online


def fetch_techmeme(src: dict) -> list[Event]:
    """Techmeme Events — editör küratörlü tek sayfalık küresel etkinlik takvimi.

    Satır yapısı (item seçicisi .rhov):
        <a><div>Aug 30-Sep 7</div>
           <div>[<em>VIRTUAL:</em>] Etkinlik Adı <span>REGISTER NOW</span></div>
           <div>Şehir[, Ülke/Eyalet]</div></a>

    Genel html fetcher'ı satırın tamamını başlık sanıyor; tarih, şehir ve
    VIRTUAL etiketi başlığa gömülü kaldığı için country/online boş kalıyor,
    yuz_yuze_ulkeler kuralı işlemiyordu. Burada üç hücre ayrı ayrı okunur.
    """
    url = src.get("url", TECHMEME_URL)
    soup = BeautifulSoup(_get(url).text, "html.parser")
    item_sel = src.get("selectors", {}).get("item", ".rhov")
    today = dt.date.today()
    year, prev_month = today.year, today.month
    events: list[Event] = []

    for node in soup.select(item_sel)[: src.get("limit", 150)]:
        a = node.select_one("a")
        if not a or not a.get("href"):
            continue
        cells = a.find_all("div", recursive=False)
        if len(cells) < 2:
            continue

        marker = ""
        em = cells[1].find("em")
        if em:
            marker = em.get_text(strip=True).upper()
            em.decompose()
        for promo in cells[1].find_all("span"):     # "REGISTER NOW" rozeti
            promo.decompose()
        title = re.sub(r"\*{2,}.*?\*{2,}", "", cells[1].get_text(" ", strip=True))
        for mk in TECHMEME_MARKERS:                 # <em> dışında düz metin de gelir
            if title.upper().startswith(mk):
                marker = marker or mk
                title = title[len(mk):]
        title = re.sub(r"\s{2,}", " ", title).strip(" -–—:")
        if not title or TECHMEME_SKIP.match(title):
            continue

        date_raw = cells[0].get_text(" ", strip=True)
        start, end, smon = _techmeme_dates(date_raw, year)
        if smon and smon < prev_month:              # liste kronolojik: yıl döndü
            year += 1
            start, end, smon = _techmeme_dates(date_raw, year)
        if smon:
            prev_month = smon

        city, country, online = _techmeme_place(
            cells[2].get_text(" ", strip=True) if len(cells) > 2 else "", marker)

        events.append(Event(
            title=title,
            url=requests.compat.urljoin(url, a["href"]),
            category=src.get("category", "genel-bt"),
            source=src["id"],
            start_date=start,
            end_date=end if end != start else None,
            city=city,
            country=country,
            online=online,
            # Tarih/yer artık kesin; konu ilgisini LLM filtresi karara bağlar.
            needs_review=True,
            extra={"date_raw": date_raw},
        ))
    return events


FETCHERS = {
    "kommunity": fetch_kommunity,
    "manual": fetch_manual,
    "confstech": fetch_confstech,
    "rss": fetch_rss,
    "html": fetch_html,
    "techmeme": fetch_techmeme,
    "ddg": fetch_ddg,
}
