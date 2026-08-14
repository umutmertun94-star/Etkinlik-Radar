"""GitHub Pages'te yayınlanan statik takvim/dashboard üretici.

docs/index.html tek dosyadır: etkinlik verisi içine gömülür,
filtreleme tarayıcıda çalışır. Sunucu gerekmez.
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

DOCS = Path(__file__).resolve().parent.parent / "docs"

TEMPLATE = """<!doctype html>
<html lang="tr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Etkinlik Radarı</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;700&family=IBM+Plex+Sans:wght@400;600&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
:root{
  --ink:#16273F; --paper:#EEF2F4; --card:#FFFFFF;
  --online:#0F7C86; --yuzyuze:#B26A15; --mute:#66727F; --line:#D6DEE3;
}
*{box-sizing:border-box;margin:0}
body{background:var(--paper);color:var(--ink);font:16px/1.55 "IBM Plex Sans",sans-serif}
a{color:inherit}
header{background:var(--ink);color:#fff;padding:28px 24px}
.wrap{max-width:880px;margin:0 auto}
header h1{font:700 26px/1.1 "Space Grotesk",sans-serif;letter-spacing:.04em;text-transform:uppercase}
header .stamp{font:400 12px/1 "IBM Plex Mono",monospace;opacity:.65;margin-top:8px}
.filters{display:flex;flex-wrap:wrap;gap:8px;padding:18px 24px}
.chip{border:1px solid var(--line);background:var(--card);border-radius:999px;
  padding:5px 14px;font:400 13px "IBM Plex Mono",monospace;cursor:pointer;color:var(--mute)}
.chip.on{background:var(--ink);border-color:var(--ink);color:#fff}
.chip:focus-visible{outline:2px solid var(--online);outline-offset:2px}
main{padding:0 24px 64px}
.month{margin-top:34px}
.month h2{font:500 13px "IBM Plex Mono",monospace;letter-spacing:.14em;
  text-transform:uppercase;color:var(--mute);border-bottom:1px solid var(--line);
  padding-bottom:8px;margin-bottom:4px}
.ev{display:grid;grid-template-columns:96px 1fr;gap:16px;padding:16px 0;
  border-bottom:1px solid var(--line);position:relative}
.date{font:500 14px/1.5 "IBM Plex Mono",monospace;color:var(--ink)}
.date .yakinda{display:inline-block;width:8px;height:8px;border-radius:50%;
  background:var(--online);margin-left:6px;animation:ping 2.2s ease-out infinite}
@keyframes ping{0%{box-shadow:0 0 0 0 rgba(15,124,134,.45)}70%{box-shadow:0 0 0 9px rgba(15,124,134,0)}100%{box-shadow:0 0 0 0 rgba(15,124,134,0)}}
@media (prefers-reduced-motion:reduce){.date .yakinda{animation:none}}
.ev h3{font:600 17px/1.35 "IBM Plex Sans",sans-serif}
.ev h3 a{text-decoration:none}
.ev h3 a:hover{text-decoration:underline;text-decoration-color:var(--online)}
.meta{margin-top:5px;font:400 12.5px "IBM Plex Mono",monospace;color:var(--mute);
  display:flex;flex-wrap:wrap;gap:6px 14px}
.tag{padding:1px 8px;border-radius:3px;font-size:11.5px}
.tag.online{background:rgba(15,124,134,.12);color:var(--online)}
.tag.yuzyuze{background:rgba(178,106,21,.12);color:var(--yuzyuze)}
.empty{margin-top:48px;color:var(--mute);font-style:italic}
@media(max-width:560px){.ev{grid-template-columns:1fr}.date{font-size:13px}}
</style>
</head>
<body>
<header><div class="wrap">
  <h1>Etkinlik Radarı</h1>
  <div class="stamp">son tarama: __UPDATED__ · kaynak: otomatik haftalık tarama</div>
</div></header>
<div class="wrap">
  <nav class="filters" id="filters" aria-label="Filtreler"></nav>
  <main id="list"></main>
</div>
<script>
const EVENTS = __EVENTS_JSON__;
const LABELS = {"yapay-zeka":"Yapay Zeka","siber-guvenlik":"Siber Güvenlik",
 "kuantum":"Kuantum","veri-merkezi":"Veri Merkezi","ai-governance":"AI Governance",
 "merkez-bankaciligi":"Merkez Bankacılığı","genel-bt":"Genel BT"};
const AYLAR=["Ocak","Şubat","Mart","Nisan","Mayıs","Haziran","Temmuz","Ağustos","Eylül","Ekim","Kasım","Aralık"];
let cat="hepsi", fmt="hepsi";

function chips(){
  const cats=["hepsi",...new Set(EVENTS.map(e=>e.category))];
  const f=document.getElementById("filters"); f.innerHTML="";
  cats.forEach(c=>{
    const b=document.createElement("button");
    b.className="chip"+(cat===c?" on":"");
    b.textContent=c==="hepsi"?"Tümü":(LABELS[c]||c);
    b.onclick=()=>{cat=c;render()};
    f.appendChild(b);
  });
  [["hepsi","Her format"],["online","Online"],["yuzyuze","Yüz yüze"]].forEach(([v,l])=>{
    const b=document.createElement("button");
    b.className="chip"+(fmt===v?" on":"");
    b.textContent=l; b.onclick=()=>{fmt=v;render()};
    f.appendChild(b);
  });
}

function render(){
  chips();
  const today=new Date().toISOString().slice(0,10);
  const soon=new Date(Date.now()+14*864e5).toISOString().slice(0,10);
  let evs=EVENTS.filter(e=>e.start_date&&e.start_date>=today);
  if(cat!=="hepsi") evs=evs.filter(e=>e.category===cat);
  if(fmt==="online") evs=evs.filter(e=>e.online===true);
  if(fmt==="yuzyuze") evs=evs.filter(e=>e.online===false);
  evs.sort((a,b)=>a.start_date.localeCompare(b.start_date));
  const list=document.getElementById("list"); list.innerHTML="";
  if(!evs.length){list.innerHTML='<p class="empty">Bu filtreyle yaklaşan etkinlik yok. Filtreyi genişletmeyi deneyin.</p>';return}
  let curMonth="";
  evs.forEach(e=>{
    const m=e.start_date.slice(0,7);
    if(m!==curMonth){
      curMonth=m;
      const h=document.createElement("section"); h.className="month";
      const n=evs.filter(x=>x.start_date.slice(0,7)===m).length;
      h.innerHTML=`<h2>${AYLAR[+m.slice(5)-1]} ${m.slice(0,4)} · ${n} etkinlik</h2>`;
      h.id="m"+m; list.appendChild(h);
    }
    const d=document.createElement("article"); d.className="ev";
    const gun=+e.start_date.slice(8,10);
    const range=e.end_date&&e.end_date!==e.start_date?`${gun}–${+e.end_date.slice(8,10)}`:`${gun}`;
    const ping=e.start_date<=soon?'<span class="yakinda" title="14 gün içinde"></span>':"";
    const yer=e.online===true?'<span class="tag online">online</span>'
      :e.online===false?`<span class="tag yuzyuze">yüz yüze</span> ${[e.city,e.country].filter(Boolean).join(", ")}`
      :[e.city,e.country].filter(Boolean).join(", ")||"format bilinmiyor";
    d.innerHTML=`<div class="date">${range}${ping}</div>
      <div><h3><a href="${e.url}" target="_blank" rel="noopener">${e.title}</a></h3>
      <div class="meta"><span>${LABELS[e.category]||e.category}</span><span>${yer}</span><span>kaynak: ${e.source}</span></div></div>`;
    document.getElementById("m"+m).appendChild(d);
  });
}
render();
</script>
</body>
</html>
"""


def write_dashboard(all_events: dict[str, dict]) -> Path:
    DOCS.mkdir(parents=True, exist_ok=True)
    shown = [e for e in all_events.values() if e.get("start_date") and not e.get("needs_review")]
    html = TEMPLATE.replace(
        "__EVENTS_JSON__", json.dumps(shown, ensure_ascii=False)
    ).replace(
        "__UPDATED__", dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    )
    out = DOCS / "index.html"
    out.write_text(html, encoding="utf-8")
    # veriyi ayrıca ham JSON olarak da yayınla (başka araçlara beslemek için)
    (DOCS / "events.json").write_text(
        json.dumps(shown, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    return out
