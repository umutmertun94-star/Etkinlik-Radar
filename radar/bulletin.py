"""Haftalık bülten üretici — başlık + link + tarih formatı."""
from __future__ import annotations

import datetime as dt
from pathlib import Path

OUT_DIR = Path(__file__).resolve().parent.parent / "output"

CATEGORY_LABELS = {
    "yapay-zeka": "Yapay Zeka",
    "siber-guvenlik": "Siber Güvenlik",
    "kuantum": "Kuantum",
    "veri-merkezi": "Veri Merkezi",
    "ai-governance": "AI Governance",
    "merkez-bankaciligi": "Merkez Bankacılığı / Ödeme Sistemleri",
    "genel-bt": "Genel BT",
}


def _fmt(e: dict) -> str:
    date = e.get("start_date") or e.get("extra", {}).get("date_raw") or "tarih belirtilmemiş"
    if e.get("end_date") and e.get("end_date") != e.get("start_date"):
        date += f" → {e['end_date']}"
    place = "Online" if e.get("online") else (
        ", ".join(x for x in (e.get("city"), e.get("country")) if x) or "format bilinmiyor"
    )
    return f"- [{e['title']}]({e['url']}) — {date} — {place} _(kaynak: {e['source']})_"


def write_bulletin(new_events: list[dict], all_events: dict[str, dict]) -> Path:
    today = dt.date.today()
    year, week, _ = today.isocalendar()
    path = OUT_DIR / f"bulten-{year}-H{week:02d}.md"
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    lines = [f"# Etkinlik Radarı — {year} / {week}. Hafta", ""]

    confirmed = [e for e in new_events if not e.get("needs_review")]
    leads = [e for e in new_events if e.get("needs_review")]

    lines += [f"## Bu hafta bulunan yeni etkinlikler ({len(confirmed)})", ""]
    if confirmed:
        for cat, label in CATEGORY_LABELS.items():
            group = [e for e in confirmed if e["category"] == cat]
            if group:
                lines.append(f"### {label}")
                lines += [_fmt(e) for e in sorted(group, key=lambda x: x.get("start_date") or "9999")]
                lines.append("")
    else:
        lines += ["Bu hafta doğrulanmış yeni etkinlik bulunamadı.", ""]

    # önümüzdeki 30 gün — hatırlatma bölümü
    horizon = (today + dt.timedelta(days=30)).isoformat()
    upcoming = [
        e for e in all_events.values()
        if e.get("start_date") and today.isoformat() <= e["start_date"] <= horizon
    ]
    if upcoming:
        lines += [f"## Önümüzdeki 30 gün ({len(upcoming)})", ""]
        lines += [_fmt(e) for e in sorted(upcoming, key=lambda x: x["start_date"])]
        lines.append("")

    if leads:
        lines += [
            f"## Doğrulanacak ipuçları ({len(leads)})",
            "_Arama/alerts kaynaklı; tarih ve format kontrol edilmeli._", "",
        ]
        lines += [_fmt(e) for e in leads[:40]]
        lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")
    return path
