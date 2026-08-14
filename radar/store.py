"""Depolama + tekilleştirme.

Tüm etkinlikler data/events.json içinde tutulur (git ile versiyonlanır).
Yeni tarama sonuçları mevcutlarla birleştirilir; yalnızca ilk kez görülen
kayıtlar 'yeni' olarak döner ve haftalık bültene girer.
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

from .models import Event

DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "events.json"


def load() -> dict[str, dict]:
    if DATA_FILE.exists():
        return {e["id"]: e for e in json.loads(DATA_FILE.read_text(encoding="utf-8"))}
    return {}


def save(events: dict[str, dict]) -> None:
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    ordered = sorted(events.values(), key=lambda e: (e.get("start_date") or "9999", e["title"]))
    DATA_FILE.write_text(
        json.dumps(ordered, ensure_ascii=False, indent=1), encoding="utf-8"
    )


def merge(existing: dict[str, dict], fetched: list[Event]) -> list[dict]:
    """Yeni bulunanları existing'e ekler, yeni eklenenleri döner."""
    today = dt.date.today().isoformat()
    new: list[dict] = []
    for ev in fetched:
        if not ev.title or not ev.url:
            continue
        if ev.id in existing:
            # tarih/yer bilgisi sonradan netleşmişse güncelle
            cur = existing[ev.id]
            for f in ("start_date", "end_date", "city", "country", "online"):
                val = getattr(ev, f)
                if val is not None and cur.get(f) is None:
                    cur[f] = val
            continue
        ev.first_seen = today
        d = ev.to_dict()
        existing[ev.id] = d
        new.append(d)
    return new


def prune(existing: dict[str, dict], keep_past_days: int = 30) -> None:
    """Bitişi eskimiş etkinlikleri arşiv dışına atmak yerine sadece
    dashboard'dan düşürmek için burada silmiyoruz; tarihi çok eski ve
    doğrulanmamış ipuçlarını temizliyoruz."""
    cutoff = (dt.date.today() - dt.timedelta(days=keep_past_days)).isoformat()
    for eid in list(existing):
        e = existing[eid]
        end = e.get("end_date") or e.get("start_date")
        if end and end < cutoff:
            del existing[eid]
