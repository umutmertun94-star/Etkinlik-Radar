"""Etkinlik veri modeli."""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field, asdict


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())


@dataclass
class Event:
    title: str
    url: str
    category: str            # yapay-zeka | siber-guvenlik | kuantum | veri-merkezi | ai-governance | merkez-bankaciligi | genel-bt
    source: str               # kaynak adı (sources.yaml'daki id)
    start_date: str | None = None   # ISO: YYYY-MM-DD (bilinmiyorsa None)
    end_date: str | None = None
    city: str | None = None
    country: str | None = None
    online: bool | None = None      # True=online, False=yüz yüze, None=bilinmiyor
    first_seen: str | None = None   # bu sistemin etkinliği ilk gördüğü tarih
    needs_review: bool = False      # tarih/format doğrulanmalı (ör. Google Alerts ipuçları)
    extra: dict = field(default_factory=dict)

    @property
    def id(self) -> str:
        key = _norm(self.title) + "|" + (self.start_date or _norm(self.url))
        return hashlib.sha1(key.encode()).hexdigest()[:16]

    def to_dict(self) -> dict:
        d = asdict(self)
        d["id"] = self.id
        return d
