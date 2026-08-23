# -*- coding: utf-8 -*-
"""raw_spots.json を都市ごとにGeminiで名寄せ・統合し、merged_{city}.json を出力する。"""
import json, io, os, time, collections

from google import genai
from google.genai import types

client = genai.Client(vertexai=True,
                      project=os.environ.get("GCP_PROJECT", "central-bulwark-427114-j7"),
                      location="global")
MODEL = "gemini-3.5-flash"

SCHEMA = {
    "type": "object",
    "properties": {
        "spots": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name_ja": {"type": "string", "description": "代表とする日本語表記名"},
                    "name_local": {"type": "string", "description": "現地語(または英語)の正式名称"},
                    "category": {"type": "string"},
                    "lat": {"type": "number"},
                    "lng": {"type": "number"},
                    "approx": {"type": "boolean", "description": "座標が店単位で正確と確信できない場合 true"},
                    "desc": {"type": "string", "description": "統合した説明（日本語1〜2文。どんな場所か+動画で何が推されていたか）"},
                    "members": {"type": "array", "items": {"type": "integer"},
                                "description": "統合した元エントリの idx（1つ以上）"},
                },
                "required": ["name_ja", "name_local", "category", "lat", "lng",
                             "approx", "desc", "members"],
            },
        },
    },
    "required": ["spots"],
}

PROMPT = """以下はベトナム旅行Vlog複数本から抽出したスポットの生リストです（同じ都市のもの）。
複数の動画に登場する同一スポットが別エントリになっているので、名寄せして1スポット=1エントリに統合してください。

ルール:
- 表記揺れ（日本語表記違い・現地語/英語表記違い・略称）でも同一施設なら必ず統合する。members に元 idx を全て入れる。
- 全ての idx がどれか1つのスポットの members に含まれること（取りこぼし禁止・重複割当禁止）。
- 別の店・別支店は統合しない（チェーン店の別支店は「店名 (通り名)」等で区別して残す）。
- 座標は precise=true のエントリの値を優先。全て曖昧なら最良の推定を入れ approx=true。
- desc は各エントリの説明を要約統合し、複数動画で推されている場合はその旨が伝わるように。
- category は最頻のものを選ぶ。
- 明らかに施設でないもの（「ベトナムコーヒー」のような一般名詞のみ等）は該当なしだが、基本は全idx をどこかに割り当てる。

生リスト:
"""

def main():
    base = os.path.dirname(os.path.abspath(__file__))
    raw = json.load(io.open(os.path.join(base, "raw_spots.json"), encoding="utf-8"))
    for i, s in enumerate(raw):
        s["idx"] = i
    by_city = collections.defaultdict(list)
    for s in raw:
        by_city[s["city"]].append(s)
    for city, items in by_city.items():
        out = os.path.join(base, f"merged_{city}.json")
        if os.path.exists(out):
            print(city, "skip", flush=True)
            continue
        listing = "\n".join(
            f'idx={s["idx"]} | {s["name_ja"]} | {s["name_local"]} | {s["category"]} | '
            f'({s["lat"]},{s["lng"]},{"precise" if s["precise"] else "approx"}) | {s["desc_ja"]}'
            for s in items)
        for attempt in range(3):
            try:
                t0 = time.time()
                res = client.models.generate_content(
                    model=MODEL, contents=PROMPT + listing,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json", response_schema=SCHEMA,
                        temperature=0.1, max_output_tokens=65000))
                data = json.loads(res.text)
                json.dump(data, io.open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
                got = sorted(i for sp in data["spots"] for i in sp["members"])
                want = sorted(s["idx"] for s in items)
                missing = set(want) - set(got)
                dup = [i for i, c in collections.Counter(got).items() if c > 1]
                print(f"{city}: in={len(items)} out={len(data['spots'])} "
                      f"missing={sorted(missing)} dup={dup} {time.time()-t0:.0f}s", flush=True)
                break
            except Exception as e:
                print(f"{city} attempt{attempt+1} ERROR {type(e).__name__}: {str(e)[:200]}", flush=True)
                time.sleep(15)
    print("done", flush=True)

if __name__ == "__main__":
    main()
