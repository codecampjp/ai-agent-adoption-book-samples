# 第4章 サンプルコード（ツール連携とFunction Calling）

本書 第4章の掲載コードを、そのまま実行できる形にまとめたもの。
ファイル名の先頭は対応する節番号（例 `4-2_` = 4-2節）。

| ファイル | 対応節 | 内容 |
|---------|-------|------|
| `4-2_function_calling_minimal.py` | 4-2 / 4-3 | 1つのツール（架空の在庫照会 get_stock）で tool_use → tool_result の往復を回す。APIキーなしでも構造を表示するドライラン付き |

## 動作確認バージョン

- Python 3.10 以上（3.10〜3.12 を推奨）
- anthropic 0.40 以上（`requirements.txt` に記載。本番モードのみ必要）

> **モデル名は実行時に最新を確認する**
>
> サンプル冒頭の `MODEL`（例 `claude-sonnet-4-6`）は、新しい世代が出るたびに更新される。
> 実行時は Anthropic 公式ドキュメントで現行のモデル名を確認して置き換えること。
> tools / tool_use / tool_result のやり取りの「型」はモデルが新しくなっても変わらない。

## 実行

### ドライラン（APIキー不要・依存なし）

API は呼ばず、Function Calling の一往復の構造とダミー実行の流れを表示する。

```bash
cd samples
python 4-2_function_calling_minimal.py
```

### 本番（実際にモデルに判断・回答させる／任意）

`anthropic` パッケージと API キーが必要。

```bash
cd samples
python3 -m venv .venv
source .venv/bin/activate        # Windows は .venv\Scripts\activate
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...      # Windows は set ANTHROPIC_API_KEY=...
python 4-2_function_calling_minimal.py
```

API キーが未設定、または `anthropic` 未導入のときは、自動でドライランに切り替わる。

## 期待される出力（ドライラン）

```text
[メモ] ANTHROPIC_API_KEY 未設定のため、API は呼ばずに流れだけを表示します。
質問: 商品A-100の在庫はいくつ？

① アプリ → モデル：tools とユーザーの質問を送る
   tools = ['get_stock']

② モデル → アプリ：tool_use を返す（実際にはモデルが判断する部分）
   stop_reason = 'tool_use'
   tool_use = {'name': 'get_stock', 'input': {'product_code': 'A-100'}}

③ アプリ：ツールを実行する
   get_stock(product_code='A-100') -> '42'

④ アプリ → モデル：tool_result を返す（tool_use_id で対応づけ）
   tool_result.content = '42'

⑤ モデル：結果を踏まえて最終回答（例：『商品A-100の在庫は42個です』）
```

本番モードでは、上記の往復を実際に Claude が判断して回し、最終回答（例「商品A-100の在庫は42個です」）を表示する。`B-200`（在庫0）や存在しない商品コードを尋ねると、モデルの応答がどう変わるかも試せる。
