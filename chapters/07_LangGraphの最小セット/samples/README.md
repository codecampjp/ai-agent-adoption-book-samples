# 第7章 サンプルコード（LangGraphの最小セット）

本書 第7章の掲載コードを、そのまま実行できる形にまとめたもの。
ファイル名の先頭は対応する節番号（例 `7-5_` = 7-5節）。

本文では「状態・ノード・エッジ・分岐・戻り線」という**構造**に集中するため、
モデルやツールの準備といった周辺コードを省いて骨格だけを掲載している。
ここではその周辺コードを補い、実際に動かせるようにしている。

| ファイル | 対応節 | 内容 |
|---------|-------|------|
| `7-2_minimal_graph.py` | 7-2 | 状態を1つ持ち、1ノードを通すだけの最小グラフ。LLM 不要でそのまま動く |
| `7-5_react_graph.py` | 7-5 | 手書き ReAct ループを StateGraph で組み直した版。モデルノード・ツールノード・条件分岐・戻り線。擬似モデルでドライラン可 |
| `7-6_checkpoint.py` | 7-6 | InMemorySaver＋`thread_id` で会話を継続。同じ ID は前回の状態を覚え、別 ID はまっさらから始まる。LLM 不要 |
| `7-7_interrupt.py` | 7-7 | `interrupt` で止め、`Command(resume=値)` で再開する HITL の往復。承認（True）・却下（False）の両方を実演。LLM 不要 |

## 動作確認バージョン

- Python 3.10 以上（実行確認は 3.12）
- langgraph 0.2 以上 / langchain-core 0.3 以上（`requirements.txt`）

> **モデル名は実行時に最新を確認する**
>
> 本番モードのモデル名（例 `claude-sonnet-4-6`）は世代交代で変わる。
> 実行時は公式ドキュメントで現行のモデル名を確認して置き換えること。
> 確かめたいのは「状態・ノード・エッジでループを組む骨格」であり、
> この骨格はモデルが新しくなっても変わらない。

## 実行

### セットアップ

```bash
cd samples
python3 -m venv .venv
source .venv/bin/activate        # Windows は .venv\Scripts\activate
pip install -r requirements.txt
```

### ドライラン（APIキー不要）

`7-5_` は擬似モデル（FakeReActModel）で「A-100 を確認 → 品切れ →
B-200 を確認 → 在庫あり → 最終回答」という ReAct ループを回す。

```bash
python 7-2_minimal_graph.py
python 7-5_react_graph.py
python 7-6_checkpoint.py
python 7-7_interrupt.py
```

### 本番モード（実際のモデルに自走させる／任意）

`langchain` と `langchain-anthropic`、API キーが必要。

```bash
pip install langchain langchain-anthropic
export ANTHROPIC_API_KEY=sk-ant-...      # Windows は set ANTHROPIC_API_KEY=...
python 7-5_react_graph.py
```

API キーが未設定、または依存が未導入のときは自動でドライランに切り替わる。

## 期待される出力

### `7-2_minimal_graph.py`

```text
{'value': '処理 された'}
```

### `7-5_react_graph.py`（ドライラン）

```text
[メモ] ANTHROPIC_API_KEY 未設定のため、擬似モデルで流れだけを表示します。

[HumanMessage] 商品A-100の在庫を確認して。品切れなら代替品B-200の在庫も調べて、まとめて報告して。
[AIMessage] tool_calls=[{'name': 'get_stock', 'args': {'product_code': 'A-100'}, 'id': 'call-a', 'type': 'tool_call'}]
[ToolMessage] 0
[AIMessage] tool_calls=[{'name': 'get_stock', 'args': {'product_code': 'B-200'}, 'id': 'call-b', 'type': 'tool_call'}]
[ToolMessage] 15
[AIMessage] 商品A-100は品切れですが、代替品B-200が15個あります。
```

`get_stock` のダミー在庫は A-100=0（品切れ）、B-200=15（在庫あり）。
在庫値を書き換えると、ループの回り方が変わる様子を試せる。

### `7-6_checkpoint.py`

```text
[thread-1]
  user> こんにちは、私はボブです。
  bot > こんにちは。
  user> 私の名前は何でしたか？
  bot > あなたの名前はボブです。

[thread-2]（別スレッド＝記憶なし）
  user> 私の名前は何でしたか？
  bot > まだ名前を教わっていません。
```

同じ `thread_id` なら前回の会話を覚え、別 `thread_id` ならまっさらから始まる。
これがチェックポインターによる状態の永続化。

### `7-7_interrupt.py`

```text
[承認するケース]
  一時停止: 「10000円の決済を承認しますか？」
  人間の判断: 承認 → Command(resume=True) で再開
    → 決済を実行しました（10000円）

[却下するケース]
  一時停止: 「10000円の決済を承認しますか？」
  人間の判断: 却下 → Command(resume=False) で再開
    → 却下されたので何もしません
```

`interrupt` で止まり、`Command(resume=値)` で再開する。resume に渡した値が
`interrupt()` の戻り値になる。副作用（決済）は承認後の別ノードに置いている
（再開時にノードが頭から再実行される点への対策。7-7 参照）。
