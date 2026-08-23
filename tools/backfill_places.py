# -*- coding: utf-8 -*-
"""Google Places API (New) で全スポットの住所・営業時間・公式サイト・正確な座標を裏取りして
data/spots.json に付与する一回きりのバックフィル。リポ直下で実行:
  PLACES_API_KEY=... python tools/backfill_places.py        # dry run (places_log.json に結果)
  PLACES_API_KEY=... python tools/backfill_places.py apply  # spots.json に反映
受入条件（コード強制）: 検索ヒット + 既存座標から3km以内 + 名前の一致度が閾値以上。
不合格はスキップして places_log.json に理由を残す（既存データは変更しない）。
"""
import json, io, os, re, sys, time, math, unicodedata

import requests

API_KEY = os.environ["PLACES_API_KEY"]
APPLY = len(sys.argv) > 1 and sys.argv[1] == "apply"

FIELDS = ("places.id,places.displayName,places.formattedAddress,places.location,"
          "places.regularOpeningHours.weekdayDescriptions,places.websiteUri,places.businessStatus")

CITY_LABEL = {"hanoi": "Hanoi", "sapa": "Sa Pa", "halong": "Ha Long", "danang": "Da Nang",
              "hoian": "Hoi An", "hcmc": "Ho Chi Minh City"}

def norm(s):
    s = unicodedata.normalize("NFD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[đĐ]", "d", s).lower()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()

def sim_token(a, b):
    ta, tb = set(norm(a).split()), set(norm(b).split())
    ta = {t for t in ta if len(t) > 1}; tb = {t for t in tb if len(t) > 1}
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / min(len(ta), len(tb))

def sim_bigram(a, b):
    # 日本語表記同士の比較用: NFKC正規化して記号・空白を除いた文字バイグラムの重なり
    def grams(s):
        s = unicodedata.normalize("NFKC", s or "").lower()
        s = re.sub(r"[^\w]", "", s, flags=re.UNICODE)
        return {s[i:i+2] for i in range(len(s) - 1)}
    ga, gb = grams(a), grams(b)
    if not ga or not gb:
        return 0.0
    return len(ga & gb) / min(len(ga), len(gb))

def sim(spot, cand_name):
    return max(sim_token(cand_name, spot.get("local", "")),
               sim_token(cand_name, spot["name"]),
               sim_bigram(cand_name, spot["name"]),
               sim_bigram(cand_name, spot.get("local", "")))

# 名称が言語違い(英語⇔日本語⇔越語)で機械判定できないが、目視で正解と確認済みのスポット。
# 最上位候補を採用する。
OVERRIDE = {"st-joseph-s-cathedral", "chua-cau", "buu-dien-trung-tam-sai-gon",
            "tru-so-uy-ban-nhan-dan-thanh-pho-ho-chi", "chua-ngoc-hoang",
            "winmart-vincom-center"}
# 自然地形などPlaces情報を付けない・座標を動かさないスポット
EXCLUDE = {"vinh-ha-long", "luon-cave"}

def dist_km(lat1, lng1, lat2, lng2):
    r = 6371
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lng2 - lng1)
    a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2*r*math.asin(math.sqrt(a))

def search(query, lat, lng):
    r = requests.post(
        "https://places.googleapis.com/v1/places:searchText",
        headers={"X-Goog-Api-Key": API_KEY, "X-Goog-FieldMask": FIELDS,
                 "Content-Type": "application/json"},
        json={"textQuery": query, "languageCode": "ja", "maxResultCount": 3,
              "locationBias": {"circle": {"center": {"latitude": lat, "longitude": lng},
                                          "radius": 15000}}},
        timeout=30)
    r.raise_for_status()
    return r.json().get("places", [])

def main():
    d = json.load(io.open("data/spots.json", encoding="utf-8"))
    log = []
    n_ok = n_skip = 0
    for s in d["spots"]:
        if s.get("place_id") or s["slug"] in EXCLUDE:
            continue
        q = f"{s.get('local') or s['name']} {CITY_LABEL[s['area']]}"
        try:
            places = search(q, s["lat"], s["lng"])
        except Exception as e:
            log.append({"slug": s["slug"], "ok": False, "why": f"api error {str(e)[:80]}"})
            n_skip += 1
            continue
        best = None
        for i, p in enumerate(places):
            name = p.get("displayName", {}).get("text", "")
            dk = dist_km(s["lat"], s["lng"], p["location"]["latitude"], p["location"]["longitude"])
            score = sim(s, name)
            if (s["slug"] in OVERRIDE and i == 0) or \
               (score >= 0.85 and dk <= 25.0) or (score >= 0.5 and dk <= 3.0):
                best = (p, name, dk, score)
                break
        if not best:
            cand = [(p.get("displayName", {}).get("text", ""),
                     round(dist_km(s["lat"], s["lng"], p["location"]["latitude"],
                                   p["location"]["longitude"]), 2)) for p in places]
            log.append({"slug": s["slug"], "name": s["name"], "ok": False,
                        "why": "no match", "candidates": cand})
            n_skip += 1
            continue
        p, name, dk, score = best
        rec = {"slug": s["slug"], "name": s["name"], "ok": True, "matched": name,
               "dist_km": round(dk, 2), "score": round(score, 2),
               "status": p.get("businessStatus", ""), "web": p.get("websiteUri", "")}
        log.append(rec)
        n_ok += 1
        if APPLY:
            s["place_id"] = p["id"]
            s["address"] = p.get("formattedAddress", "")
            hours = p.get("regularOpeningHours", {}).get("weekdayDescriptions")
            if hours:
                s["hours"] = hours
            if p.get("websiteUri"):
                s["url"] = p["websiteUri"]
            s["lat"] = round(p["location"]["latitude"], 6)
            s["lng"] = round(p["location"]["longitude"], 6)
            s["approx"] = False
        time.sleep(0.12)
        print(f"{'OK ' if rec['ok'] else 'NG '}{s['slug']} -> {name} ({dk:.2f}km, {score:.2f})", flush=True)
    if APPLY:
        json.dump(d, io.open("data/spots.json", "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
    json.dump(log, io.open("places_log.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    closed = [r["slug"] for r in log if r.get("ok") and r.get("status") not in ("OPERATIONAL", "")]
    print(f"done: ok={n_ok} skip={n_skip} apply={APPLY}")
    print("non-operational:", closed)

if __name__ == "__main__":
    main()
