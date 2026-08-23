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
- `data/videos.json` — YouTube出典のメタ情報（動画ID → タイトル/チャンネル/ponpokoフラグ）
- `data/config.json` — タイトル・リード文・地図中心/ズーム等
- `validate.py` — データ整合性チェック（`python validate.py`）

`spots.json` のスポットは `sources` 配列で出典を持つ:

```json
{"type": "youtube", "id": "3pU_mJFd-E8"}
```

ぽんぽこちゃんねるの動画が出典に含まれるスポットは `"ponpoko": true` を持ち、
UI側でスポット名・地図ラベル・詳細モーダルに 🍃 が表示される（validate.py が整合を検査）。

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
