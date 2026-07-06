# 第8章 サンプルコード（自作MCPサーバーを書く）

本書 第8章の掲載コードを、そのまま実行できる形にまとめたもの。
ファイル名の先頭は対応する節番号（例 `8-1_` = 8-1節）。

本文では「サーバーがどんな部品でできているか」という**構造**に集中するため、
動かすための周辺コードを省いて骨格だけを掲載している。
ここではその周辺コードを補い、実際に動かせるようにしている。

通常、stdio で動くMCPサーバーは `mcp.run()` で起動し、ホスト（AIアプリ）からの接続を待ち受ける。
ただ、それだとホストを用意しないと動きを確認できない。そこで各サンプルは、
**APIキー・ネットワーク不要のドライラン**として、FastMCP のインメモリ Client で自分のサーバーにつなぎ、
`tools/list`（道具の一覧）・`tools/call`（実行）・`resources/read`（リソース読み取り）などを確かめる。
`--serve` を付けると、本物の stdio サーバーとして起動する（Claude Desktop などのホストから接続する用）。

| ファイル | 対応節 | 内容 |
|---------|-------|------|
| `8-1_minimal_server.py` | 8-1 | 足し算の道具を1つ公開する最小サーバー。インメモリ Client で発見・実行を確認 |
| `8-3_primitives.py` | 8-3 | ツール・リソース・プロンプトの3分類を1つのサーバーにまとめた版。テンプレート（`customer://{id}`）も実演 |
| `8-4_internal_api_server.py` | 8-4 | 社内APIを `httpx`（非同期）で叩く在庫サーバー。環境変数が未設定ならダミー在庫でドライラン |

## 動作確認バージョン

- Python 3.10 以上（実行確認は 3.12）
- fastmcp 3.x（`requirements.txt`。実行確認は 3.4.2、下層 `mcp` 1.28.1）

> **バージョンは固定する**
>
> 独立パッケージ `fastmcp` は更新が速く、メジャー版の切り替わりで破壊的変更が入る
> （v2→v3 でデコレータの書き方やサーバー設定が変わった）。本書で使う最小の書き方
> （`@mcp.tool` / `mcp.run()`）は版をまたいで安定だが、本番では依存版を固定すること。

## 実行

### セットアップ

```bash
cd samples
python3 -m venv .venv
source .venv/bin/activate        # Windows は .venv\Scripts\activate
pip install -r requirements.txt
# uv を使う場合:
#   uv venv --python 3.12 .venv
#   uv pip install --python .venv -r requirements.txt
```

### ドライラン（APIキー・ネットワーク不要）

```bash
python 8-1_minimal_server.py
python 8-3_primitives.py
python 8-4_internal_api_server.py
```

### 本物のサーバーとして起動する（任意）

```bash
python 8-1_minimal_server.py --serve   # stdio サーバーとして起動（ホストから接続）
```

MCP Inspector や Claude Desktop からの接続方法は本文 8-6 を参照。
`8-4` を本物の社内APIにつなぐ場合は、環境変数を渡して起動する。

```bash
export INVENTORY_API_BASE=https://api.example.internal
export INVENTORY_API_KEY=...            # 資格情報はコードに直書きしない
python 8-4_internal_api_server.py
```

## 期待される出力

### `8-1_minimal_server.py`

```text
[tools/list] 公開中の道具: ['add']
[tools/call] add(2, 3) -> 5
```

### `8-3_primitives.py`

```text
[tools/list] ['create_ticket']
[tools/call] create_ticket -> {'id': 'TICKET-0001', ...}
[resources/list] ['config://app']
[resource templates] ['customer://{customer_id}']
[resources/read] config://app -> {"version": "1.0", "region": "tokyo"}
[resources/read] customer://12345 -> {"name": "山田太郎", "plan": "standard"}
[prompts/list] ['summarize_complaint']
```

### `8-4_internal_api_server.py`（ドライラン）

```text
[tools/list] ['get_stock']
[tools/call] get_stock(A-100) -> {'product_code': 'A-100', 'stock': 0}
[tools/call] get_stock(B-200) -> {'product_code': 'B-200', 'stock': 15}
```

ダミー在庫は A-100=0（品切れ）、B-200=15（在庫あり）。
環境変数を設定すると、ダミーの代わりに本物の社内APIを叩く（本文 8-4 の `httpx` 経路）。
