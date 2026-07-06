# 第3章 サンプルコード（ベクターDBとRAG）

本書 第3章の掲載コードを、そのまま実行できる形にまとめたもの。
ファイル名の先頭は対応する節番号（例 `3-3_` = 3-3節）。

| ファイル | 対応節 | 内容 |
|---------|-------|------|
| `3-3_rag_minimal.py` | 3-3 | Chromaで最小のRAG（取り込み→検索）。APIキー不要 |
| `3-4_rag_with_generation.py` | 3-4 | 検索結果をプロンプトに差し込んで組み立て、任意でClaudeに渡す |

## 動作確認バージョン

- Python 3.10 以上（3.10〜3.12 を推奨）
- chromadb 1.5.x / sentence-transformers 5.x（`requirements.txt` に記載）

## セットアップ

### 方法A: uv（推奨・高速）

```bash
cd samples
uv venv
source .venv/bin/activate        # Windows は .venv\Scripts\activate
uv pip install -r requirements.txt
```

### 方法B: 標準の venv + pip

```bash
cd samples
python3 -m venv .venv
source .venv/bin/activate        # Windows は .venv\Scripts\activate
pip install -r requirements.txt
```

> **初回実行時の注意：埋め込みモデルのダウンロード**
>
> 3-3 / 3-5 は日本語対応の埋め込みモデル `paraphrase-multilingual-MiniLM-L12-v2`
> （約 0.5GB）を初回に自動ダウンロードする。ネットワーク接続と数分の待ち時間が必要。
> 2回目以降はローカルキャッシュ（`~/.cache/huggingface/`）から読み込むため高速。

## 実行

```bash
# 3-3: 取り込み→検索
python 3-3_rag_minimal.py

# 3-4: 検索→プロンプト組み立て（生成はAPIキーがあれば実行）
python 3-4_rag_with_generation.py
```

### 3-4 で実際に生成まで試す場合（任意）

`anthropic` パッケージと API キーが必要。

```bash
pip install anthropic
export ANTHROPIC_API_KEY=sk-ant-...      # Windows は set ANTHROPIC_API_KEY=...
python 3-4_rag_with_generation.py
```

API キーが未設定のときは、組み立てたプロンプトの表示までで止まる（生成はスキップ）。

## 期待される出力（3-3）

```text
Q: 休みを取りたいときの手続きは？
 -> 年次有給休暇は入社半年後に10日付与され、勤怠システムから前日までに申請します。
Q: 立て替えたお金はどう請求する？
 -> 出張旅費や立替経費は、月末締めで翌月10日までに領収書を添付して経費システムへ申請します。
Q: 機密情報の保管ルールは？
 -> 社外秘データは指定の暗号化ストレージに保管し、パスワードは90日ごとに変更してください。
```
