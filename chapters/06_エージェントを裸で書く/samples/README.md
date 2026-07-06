# 第6章 サンプルコード（エージェントを裸で書く）

本書 第6章の掲載コードを、そのまま実行できる形にまとめたもの。
ファイル名の先頭は対応する節番号（例 `6-4_` = 6-4節）。

第4章の「ツール使用の一往復」を `while` ループで包み、モデルが道具を要求しなくなる
まで自走させる、最小のエージェントを段階的に組み立てる。

| ファイル | 対応節 | 内容 |
|---------|-------|------|
| `6-4_agent_loop_minimal.py` | 6-4 | 最小エージェントループ。`while True` で tool_use を回し、最終回答で抜ける。コメント (a)〜(d) は本文・図6-4-1 と対応 |
| `6-6_agent_loop_observable.py` | 6-5 / 6-6 | 6-4 に「停止条件（最大反復回数）」と「ステップごとのログ」を足した版。ツールは `6-4_` から再利用 |

## 動作確認バージョン

- Python 3.10 以上（3.10〜3.12 を推奨。実行確認は 3.12）
- anthropic 0.40 以上（`requirements.txt` に記載。本番モードのみ必要）

> **モデル名は実行時に最新を確認する**
>
> サンプル冒頭の `MODEL`（例 `claude-sonnet-4-6`）は、新しい世代が出るたびに更新される。
> 実行時は Anthropic 公式ドキュメントで現行のモデル名を確認して置き換えること。
> 確かめたいのはモデルの賢さではなく「ツール使用をループで回す骨格」であり、
> この骨格はモデルが新しくなっても変わらない。
> （`6-6_` は `6-4_` の `MODEL` を共有するので、更新は `6-4_` 側だけでよい）

## 実行

### ドライラン（APIキー不要・依存なし）

API は呼ばず、エージェントループがどう回るか（A-100 が品切れ→代替品 B-200 を確認→
最終回答）の流れと、各ステップのログの形を表示する。

```bash
cd samples
python 6-4_agent_loop_minimal.py
python 6-6_agent_loop_observable.py
```

### 本番（実際にモデルに自走させる／任意）

`anthropic` パッケージと API キーが必要。

```bash
cd samples
python3 -m venv .venv
source .venv/bin/activate        # Windows は .venv\Scripts\activate
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...      # Windows は set ANTHROPIC_API_KEY=...
python 6-4_agent_loop_minimal.py
python 6-6_agent_loop_observable.py
```

API キーが未設定、または `anthropic` 未導入のときは、自動でドライランに切り替わる。

## 期待される出力

### `6-4_agent_loop_minimal.py`（ドライラン）

```text
[メモ] ANTHROPIC_API_KEY 未設定のため、API は呼ばずに流れだけを表示します。
依頼: 商品A-100の在庫を確認して。品切れなら代替品B-200の在庫も調べて、両方まとめて報告して。

(a) 1回目の問い合わせ → モデルは get_stock を要求（stop_reason='tool_use'）
(c) アプリがツールを実行：get_stock(product_code='A-100') -> '0'
    観察：在庫0（品切れ）→ モデルは『代替品も調べよう』と判断

(a) 2回目の問い合わせ → モデルは get_stock を要求（stop_reason='tool_use'）
(c) アプリがツールを実行：get_stock(product_code='B-200') -> '15'
    観察：在庫15（あり）→ 必要な情報がそろった

(b) 次の問い合わせでモデルは道具を要求しない（stop_reason は tool_use 以外）
(d) ループを抜ける → 最終回答（例：『商品A-100は品切れですが、代替品B-200が15個あります』）
```

### `6-6_agent_loop_observable.py`（ドライラン）

本文 6-6 の「期待される記録」と同じ形のステップログを再現する。

```text
[step 0] stop_reason=tool_use tokens(in/out)=512/45
[step 0] tool=get_stock input={'product_code': 'A-100'} -> 0
[step 1] stop_reason=tool_use tokens(in/out)=580/48
[step 1] tool=get_stock input={'product_code': 'B-200'} -> 15
[step 2] stop_reason=end_turn tokens(in/out)=640/60
```

本番モードでは、上記のループを実際に Claude が判断して回す。`get_stock` のダミー在庫は
A-100=0（品切れ）、B-200=15（在庫あり）。在庫値を書き換えると、モデルがどう
道具を呼び分け、何ステップで最終回答に至るかが変わる様子を試せる。
