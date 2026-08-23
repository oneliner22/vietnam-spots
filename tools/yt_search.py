# -*- coding: utf-8 -*-
"""YouTube検索「ベトナム vlog」の上位20件(通常動画)をInnerTube APIで取得する。"""
import json, io, requests

URL = "https://www.youtube.com/youtubei/v1/search?prettyPrint=false"
body = {
    "context": {"client": {"clientName": "WEB", "clientVersion": "2.20260801.00.00",
                            "hl": "ja", "gl": "JP"}},
    "query": "ベトナム vlog",
}
r = requests.post(URL, json=body, timeout=30,
                  headers={"User-Agent": "Mozilla/5.0", "Content-Type": "application/json"})
r.raise_for_status()
d = r.json()

def walk_video_renderers(node):
    if isinstance(node, dict):
        if "videoRenderer" in node:
            yield node["videoRenderer"]
        for v in node.values():
            yield from walk_video_renderers(v)
    elif isinstance(node, list):
        for v in node:
            yield from walk_video_renderers(v)

def txt(o):
    if not o: return ""
    if "simpleText" in o: return o["simpleText"]
    return "".join(run.get("text", "") for run in o.get("runs", []))

seen, out = set(), []
for vr in walk_video_renderers(d):
    vid = vr.get("videoId")
    if not vid or vid in seen: continue
    seen.add(vid)
    out.append({
        "id": vid,
        "title": txt(vr.get("title")),
        "channel": txt(vr.get("ownerText") or vr.get("longBylineText")),
        "length": txt(vr.get("lengthText")),
        "views": txt(vr.get("viewCountText")),
        "published": txt(vr.get("publishedTimeText")),
    })
    if len(out) >= 20: break

with io.open("search_results.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
for i, v in enumerate(out, 1):
    print(f"{i:2d}. [{v['id']}] {v['length']:>8} {v['title'][:60]} / {v['channel']}")
