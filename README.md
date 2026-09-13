# ベトナムおすすめMAP 🍜 〜YouTube旅Vlogから〜

YouTubeで「ベトナム vlog」を検索した上位20本と、ぽんぽこちゃんねるのベトナム動画4本を
Gemini（動画解析）で解析して抽出したベトナムのおすすめスポットを、エリア別に色分けした
地図＋一覧にまとめた静的サイト。スポットをクリックすると出典（YouTube紹介動画の埋め込み）が
モーダルで見られる。

🍃 印が付いたスポットは、**ぽんぽこちゃんねる**の動画で紹介されたスポット。

公開URL: https://oneliner22.github.io/vietnam-spots/

## 構成

- `index.html` — アプリ本体。`data/*.json` を実行時に fetch して描画（ビルド工程なし）
- `data/spots.json` — **スポットデータの正本**（エリア/カテゴリ/座標/説明/出典）
- `data/videos.json` — YouTube出典のメタ情報（動画ID → タイトル/チャンネル/markフラグ）
- `data/config.json` — タイトル・リード文・地図中心/ズーム等
- `validate.py` — データ整合性チェック（`python validate.py`）

`spots.json` のスポットは `sources` 配列で出典を持つ:

```json
{"type": "youtube", "id": "3pU_mJFd-E8"}
{"type": "x", "url": "https://x.com/<handle>/status/<id>", "author": "<handle>", "date": "2026-07-24", "quote": "..."}
{"type": "x", "anon": true, "date": "2025-09-17", "quote": "..."}
```

X出典はファンの聖地巡礼・旅行報告ポスト。`anon: true` は投稿者保護のため
ユーザー名・リンクを伏せて引用文のみ表示する出典（validate.py が整合を検査）。

自動追加された多くのスポットは Google Places API の裏取りによる
`address` / `hours`（曜日別7行・日本語）/ `url`（公式サイト）/ `place_id` を持ち、
座標も Places の値で補正済み（`tools/backfill_places.py`、一回きりのバックフィル）。

ぽんぽこちゃんねるの動画が出典に含まれるスポットは `"mark": true` を持ち、
`config.json` の `mark_emoji` / `mark_note` / `legend_extra` に従って
スポット名・地図ラベル・詳細モーダルに 🍃 が表示される（validate.py が整合を検査）。

## 閲覧側の機能（index.html に実装済み・追加データ不要）

- **ブックマーク**: ☆ でスポットをグループに保存（最大10グループ・各100件）。ログイン不要で
  ブラウザの `localStorage` にのみ保存。地図下の「⭐ ブックマーク」タブでグループ管理
  （名前変更・並べ替え・削除）、「⭐ ブックマークのみ」チップで地図と一覧を絞り込み。
- **🧭 動線**: グループ内のスポットを表示順に線で結び、番号付きマーカーを地図に描く。
- **絞り込み・並び順**: ジャンル・エリアに加えて、出典の種類（YouTube / X）、おすすめした人
  （チャンネル・X投稿者）、「指定した場所から近い順」（現在地 / 地図の中心 / スポット名を起点）。
- **ランダムおすすめ**: ヒーロー直下に 5 件（`config.json` の `reco_count`）を横スクロールで表示。
- **❓ これはなに？**: リード文・出典説明はボタンで展開する折りたたみ式。

## ローカルプレビュー

fetch を使うため file:// では動かない。リポジトリ直下で:

```
python -m http.server
# → http://localhost:8000/
```

編集後は `python validate.py` で整合性チェック。

## データの作り方（一回きり・自動収集パイプラインなし）

1. YouTube検索「ベトナム vlog」上位20件 + ぽんぽこちゃんねるの指定4本（計23本、1本重複）
2. 各動画を Gemini (Vertex AI, gemini-3.5-flash) に YouTube URL 渡しで解析し、
   登場スポット（名称/現地語名/都市/カテゴリ/座標/説明）を構造化抽出
3. 動画横断で同一スポットを名寄せ・統合し、エリアを割り当てて `data/spots.json` を生成
4. 座標は Gemini の推定値。番地まで確信が持てないものは `approx: true`（「およその位置」表示）

## 出典・クレジット

スポット情報は各YouTube動画に基づく（著作権は各投稿者に帰属）。
地図: © OpenStreetMap contributors / Leaflet。
本サイトは非公式のファンメイドまとめです。

## tools/（データ生成に使った一回きりのスクリプト）

- `tools/yt_search.py` — YouTube検索「ベトナム vlog」上位20件の取得（InnerTube API）
- `tools/analyze.py` — 各動画を Gemini (Vertex AI) で解析しスポット抽出（要 ADC / GCP_PROJECT）
- `tools/merge.py` — 都市ごとに Gemini で名寄せ・統合
- `tools/build_data.py` — `data/spots.json` / `videos.json` / `config.json` を生成

日次の自動収集パイプラインはこのサイトにはない（意図的に持たない）。
