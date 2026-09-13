# -*- coding: utf-8 -*-
"""data/*.json の整合性チェック。手動編集後に実行する。
使い方: python validate.py  (異常があれば exit 1)
"""
import json, io, re, sys

# ベトナム全土 + マージン
BBOX = {"lat_min": 7.5, "lat_max": 24.5, "lng_min": 101.5, "lng_max": 110.5}

ERRORS = []
def err(msg): ERRORS.append(msg)

def load(path):
    try:
        return json.load(io.open(path, encoding="utf-8"))
    except Exception as e:
        err(f"{path}: パース失敗 ({e})")
        return None

spots_doc = load("data/spots.json")
videos    = load("data/videos.json")
config    = load("data/config.json")

if spots_doc and videos is not None:
    areas = spots_doc.get("areas", [])
    spots = spots_doc.get("spots", [])
    area_ids = [a["id"] for a in areas]
    if len(area_ids) != len(set(area_ids)):
        err("area id が重複")

    slugs = set()
    x_url_re = re.compile(r"^https://(x|twitter)\.com/.+/status(es)?/\d+")
    mark_vids = {vid for vid, v in videos.items() if v.get("mark")}

    for s in spots:
        tag = f"spot '{s.get('slug', '?')}'"
        for key in ("slug", "name", "area", "cat", "lat", "lng", "approx", "desc", "sources"):
            if key not in s:
                err(f"{tag}: 必須キー {key} がない")
        if s.get("slug") in slugs:
            err(f"{tag}: slug 重複")
        slugs.add(s.get("slug"))
        if s.get("area") not in area_ids:
            err(f"{tag}: 未知の area '{s.get('area')}'")
        lat, lng = s.get("lat"), s.get("lng")
        if not (isinstance(lat, (int, float)) and isinstance(lng, (int, float))):
            err(f"{tag}: lat/lng が数値でない")
        elif not (BBOX["lat_min"] <= lat <= BBOX["lat_max"] and BBOX["lng_min"] <= lng <= BBOX["lng_max"]):
            err(f"{tag}: 座標 ({lat},{lng}) がマージン付きbbox外")
        if not isinstance(s.get("sources"), list) or not s["sources"]:
            err(f"{tag}: sources が空")
            continue
        for src in s["sources"]:
            t = src.get("type")
            if t == "youtube":
                if src.get("id") not in videos:
                    err(f"{tag}: videos.json にない動画ID '{src.get('id')}'")
            elif t == "x":
                if src.get("anon"):
                    # 投稿者保護のためURL・ユーザー名を持たない匿名出典
                    if not src.get("quote") or not src.get("date"):
                        err(f"{tag}: anon x source に quote/date がない")
                    continue
                if not x_url_re.match(src.get("url", "")):
                    err(f"{tag}: 不正なX URL '{src.get('url')}'")
                # /i/web/status/<id> は X のリダイレクト頼みで、年齢制限付きアカウントの
                # ポストだと未ログイン閲覧者に404が出る。著者不明のフォールバック時のみ許容
                elif "/i/web/status/" in src["url"]:
                    print(f"note: {tag}: X URL が /i/web/ 形式 (著者ハンドル不明) '{src['url']}'")
                if not src.get("date"):
                    err(f"{tag}: x source に date がない")
            else:
                err(f"{tag}: 未知の source type '{t}'")
        # mark 印: mark=true のスポットは mark 付き動画が出典に含まれていること（逆も）
        if mark_vids:
            yt_ids = {src.get("id") for src in s["sources"] if src.get("type") == "youtube"}
            if s.get("mark") and not (yt_ids & mark_vids):
                err(f"{tag}: mark=true だが出典に mark 付き動画がない")
            if not s.get("mark") and (yt_ids & mark_vids):
                err(f"{tag}: 出典に mark 付き動画があるのに mark=true でない")

if ERRORS:
    print("NG:", len(ERRORS), "件")
    for e in ERRORS:
        print(" -", e)
    sys.exit(1)

n_spots = len(spots_doc["spots"]) if spots_doc else 0
n_src = sum(len(s["sources"]) for s in spots_doc["spots"]) if spots_doc else 0
n_mark = sum(1 for s in spots_doc["spots"] if s.get("mark")) if spots_doc else 0
print(f"OK: spots={n_spots} sources={n_src} areas={len(spots_doc['areas'])} "
      f"videos={len(videos)} mark_spots={n_mark}")
