# -*- coding: utf-8 -*-
"""merged_{city}.json + raw_spots.json から vietnam-spots/data/*.json を生成する。"""
import json, io, os, re, unicodedata, collections

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

PONPOKO = {"OYDyLvNdOog", "mnOBhN454wY", "hTjgY8vdcZE", "3pU_mJFd-E8"}

AREAS = [
    {"id": "hanoi",  "name": "ハノイ",            "color": "#e8543f"},
    {"id": "sapa",   "name": "サパ",              "color": "#2f9e7d"},
    {"id": "halong", "name": "ハロン湾",          "color": "#3f7fd6"},
    {"id": "danang", "name": "ダナン",            "color": "#e0489a"},
    {"id": "hoian",  "name": "ホイアン",          "color": "#b07d2a"},
    {"id": "hcmc",   "name": "ホーチミン",        "color": "#7b5cd6"},
]
CITY2AREA = {"ハノイ": "hanoi", "サパ": "sapa", "ハロン湾": "halong",
             "ダナン": "danang", "ホイアン": "hoian", "ホーチミン": "hcmc"}
CATS = {"グルメ", "カフェ・喫茶", "観光", "レトロ", "雑貨・土産", "自然", "動物", "体験", "宿"}

raw = json.load(io.open(os.path.join(BASE, "raw_spots.json"), encoding="utf-8"))
for i, s in enumerate(raw):
    s["idx"] = i

def slugify(name_local, name_ja, used):
    s = unicodedata.normalize("NFD", name_local or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[đĐ]", "d", s)
    s = re.sub(r"[^A-Za-z0-9]+", "-", s).strip("-").lower()
    if not s:
        s = re.sub(r"[^a-z0-9]+", "-",
                   unicodedata.normalize("NFKC", name_ja).encode("ascii", "ignore").decode().lower()).strip("-")
    if not s:
        s = "spot"
    s = s[:40].rstrip("-")
    base, n = s, 2
    while s in used:
        s = f"{base}-{n}"; n += 1
    used.add(s)
    return s

spots, used = [], set()
warn = []
for city, area in CITY2AREA.items():
    path = os.path.join(BASE, f"merged_{city}.json")
    merged = json.load(io.open(path, encoding="utf-8"))
    for m in merged["spots"]:
        vids, seen = [], set()
        pp_ts = None
        for idx in m["members"]:
            r = raw[idx]
            v = r["video"]
            if v not in seen:
                seen.add(v); vids.append(v)
        # ぽんぽこ動画の出典を先頭に
        vids.sort(key=lambda v: (v not in PONPOKO,))
        cat = m["category"] if m["category"] in CATS else "観光"
        if m["category"] not in CATS:
            warn.append(f"cat fix: {m['name_ja']} {m['category']} -> 観光")
        lat, lng = m["lat"], m["lng"]
        if not (7.5 <= lat <= 24.5 and 101.5 <= lng <= 110.5):
            warn.append(f"BBOX OUT: {m['name_ja']} ({lat},{lng}) city={city}")
        spots.append({
            "slug": slugify(m["name_local"], m["name_ja"], used),
            "name": m["name_ja"],
            "local": m["name_local"],
            "area": area,
            "cat": cat,
            "lat": round(lat, 6), "lng": round(lng, 6),
            "approx": bool(m["approx"]),
            "desc": m["desc"],
            "ponpoko": any(v in PONPOKO for v in vids),
            "sources": [{"type": "youtube", "id": v} for v in vids],
        })
    print(f"{city}: {len(merged['spots'])} spots")

# ponpoko キーは true のものだけ残す（ishikawa スキーマに寄せる）
for s in spots:
    if not s["ponpoko"]:
        del s["ponpoko"]

# videos.json
search = json.load(io.open(os.path.join(BASE, "search_results.json"), encoding="utf-8"))
pmeta = json.load(io.open(os.path.join(BASE, "ponpoko_meta.json"), encoding="utf-8"))
videos = {}
for v in search:
    videos[v["id"]] = {"title": v["title"], "channel": v["channel"]}
for vid, v in pmeta.items():
    videos[vid] = {"title": v["title"], "channel": v["channel"]}
for vid in PONPOKO:
    videos[vid]["ponpoko"] = True

used_vids = {src["id"] for s in spots for src in s["sources"]}
print("videos referenced:", len(used_vids), "/", len(videos))
for vid in videos:
    if vid not in used_vids:
        print("  unreferenced video:", vid, videos[vid]["title"][:40])

n_pp = sum(1 for s in spots if s.get("ponpoko"))
print("total spots:", len(spots), " ponpoko spots:", n_pp)
for w in warn:
    print("WARN", w)

os.makedirs(OUT, exist_ok=True)
json.dump({"areas": AREAS, "spots": spots},
          io.open(os.path.join(OUT, "spots.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
json.dump(videos, io.open(os.path.join(OUT, "videos.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)

config = {
    "title": "ベトナムおすすめMAP 〜YouTube旅Vlogから〜",
    "description": "YouTubeの「ベトナム vlog」検索上位20本とぽんぽこちゃんねるのベトナム動画4本をGeminiで解析して集めたベトナムのおすすめスポットをエリア別に地図化。スポットをクリックすると紹介動画がその場で見られます。",
    "favicon": "🍜",
    "h1": "🍜 ベトナムおすすめMAP 🇻🇳",
    "lead": "YouTubeで「ベトナム vlog」を検索した上位<b>20本</b>と、<b>ぽんぽこちゃんねる</b>のベトナム動画<b>4本</b>をGemini（動画解析）で解析して集めたおすすめスポットを、ハノイからホーチミンまでエリア別にマッピング。<br>スポット名やマーカーをクリックすると、<b>紹介しているYouTube動画</b>がその場で見られます。<span class=\"leaf\">🍃</span> 付きは<b>ぽんぽこちゃんねる</b>の動画で紹介されたスポットです。",
    "meta": "出典: YouTube旅行Vlog 23本（「ベトナム vlog」検索上位20本 + ぽんぽこちゃんねる4本）をGeminiで解析",
    "footer": "動画の著作権は各投稿者に帰属します ・ 地図: © OpenStreetMap contributors / Leaflet ・ 座標はGeminiによる推定を含み、一部スポットは「およその位置」です",
    "map_center": [16.0, 106.5],
    "map_zoom": 6,
}
json.dump(config, io.open(os.path.join(OUT, "config.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("written to", OUT)
