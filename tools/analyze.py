# -*- coding: utf-8 -*-
"""各YouTube動画をGemini(Vertex AI)に渡し、登場スポットをJSONで抽出する。
analysis/{video_id}.json が既にあればスキップ（再実行可能）。"""
import json, io, os, sys, time, traceback

from google import genai
from google.genai import types

client = genai.Client(vertexai=True,
                      project=os.environ.get("GCP_PROJECT", "central-bulwark-427114-j7"),
                      location="global")
MODEL = "gemini-3.5-flash"

CATS = ["グルメ", "カフェ・喫茶", "観光", "レトロ", "雑貨・土産", "自然", "動物", "体験", "宿"]

SCHEMA = {
    "type": "object",
    "properties": {
        "video_summary": {"type": "string", "description": "動画の内容の1文要約（日本語）"},
        "cities": {"type": "array", "items": {"type": "string"},
                   "description": "動画で訪れている都市・地域（例: ハノイ, ダナン, ホイアン, ホーチミン, サパ, ハロン湾）"},
        "spots": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name_ja": {"type": "string", "description": "スポット名（日本語表記。店名はカタカナ+必要なら原語）"},
                    "name_local": {"type": "string", "description": "現地語(ベトナム語/英語)の正式名称。不明なら空文字"},
                    "city": {"type": "string", "description": "所在都市・地域（ハノイ/ダナン/ホイアン/ホーチミン/サパ/ハロン湾/フエ 等）"},
                    "category": {"type": "string", "enum": CATS},
                    "lat": {"type": "number", "description": "緯度。知っている範囲で最良の推定値"},
                    "lng": {"type": "number", "description": "経度"},
                    "precise": {"type": "boolean",
                                "description": "その店・施設の正確な場所を確信を持って特定できる場合のみtrue。曖昧ならfalse"},
                    "desc_ja": {"type": "string",
                                "description": "どんな場所か+動画内で何をした/何が推されていたか（日本語で1〜2文）"},
                    "timestamp": {"type": "string", "description": "動画内で登場するおよその時刻 mm:ss"},
                },
                "required": ["name_ja", "name_local", "city", "category", "lat", "lng",
                             "precise", "desc_ja", "timestamp"],
            },
        },
    },
    "required": ["video_summary", "cities", "spots"],
}

PROMPT = """この動画はベトナム旅行のVlogです。動画を最初から最後まで確認し、動画内で実際に訪問・紹介されている「地図に載せられる具体的なスポット」をすべて抽出してください。

対象: 飲食店、カフェ、市場、観光名所、寺院・教会、ビーチ、テーマパーク、博物館、ショップ、スパ・マッサージ店、宿泊したホテル、体験施設 など。
対象外: 空港・駅・コンビニ等の汎用施設（ただし観光対象として紹介されている場合は含める）、店名も場所も特定できない路上の屋台。

注意:
- 店名・施設名は映像内の看板・字幕・概要欄的な言及から可能な限り正確に取ること。
- 座標(lat/lng)はあなたの知識で最良の推定を入れること。正確な店の位置に自信がある場合のみ precise=true。都市中心などの粗い推定なら precise=false。
- 同じ店に複数回行っていても1件にまとめる。
- カテゴリは指定の選択肢から最も近いものを選ぶ。
"""

def analyze(vid):
    res = client.models.generate_content(
        model=MODEL,
        contents=[
            types.Part(file_data=types.FileData(
                file_uri=f"https://www.youtube.com/watch?v={vid}", mime_type="video/mp4")),
            PROMPT,
        ],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=SCHEMA,
            media_resolution=types.MediaResolution.MEDIA_RESOLUTION_LOW,
            temperature=0.2,
        ),
    )
    return json.loads(res.text)

def main():
    base = os.path.dirname(os.path.abspath(__file__))
    os.makedirs(os.path.join(base, "analysis"), exist_ok=True)
    search = json.load(io.open(os.path.join(base, "search_results.json"), encoding="utf-8"))
    ponpoko = json.load(io.open(os.path.join(base, "ponpoko_meta.json"), encoding="utf-8"))
    vids = [v["id"] for v in search] + [k for k in ponpoko if k not in {v["id"] for v in search}]
    print(f"total {len(vids)} videos", flush=True)
    for i, vid in enumerate(vids, 1):
        out = os.path.join(base, "analysis", vid + ".json")
        if os.path.exists(out):
            print(f"[{i}/{len(vids)}] {vid} skip", flush=True)
            continue
        for attempt in range(3):
            try:
                t0 = time.time()
                data = analyze(vid)
                json.dump(data, io.open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
                print(f"[{i}/{len(vids)}] {vid} ok spots={len(data['spots'])} {time.time()-t0:.0f}s", flush=True)
                break
            except Exception as e:
                print(f"[{i}/{len(vids)}] {vid} attempt{attempt+1} ERROR {type(e).__name__}: {str(e)[:200]}", flush=True)
                if attempt == 2:
                    traceback.print_exc()
                time.sleep(20)
    print("done", flush=True)

if __name__ == "__main__":
    main()
