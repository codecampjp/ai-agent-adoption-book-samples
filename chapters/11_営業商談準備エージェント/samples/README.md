# 第11章 サンプルコード（営業商談準備エージェント ── Plan-and-Execute × HITL）

本書 第11章の掲載コードを、そのまま実行できる形にまとめたもの。
ファイル名の先頭は対応する節番号（例 `11-5_` = 11-5節）。

本文では「どこで計画し、どこで人間が承認し、どこでループして実行し、どこで束ねているか」
という**構造**に集中するため、動かすための周辺コードを省いて骨格だけを掲載している。
ここではその周辺コードを補い、実際に動かせるようにしている。

すべて **APIキー・ネットワーク不要のドライラン**で動く。検索はダミーの情報源
（`_common.py`）、計画・統合は擬似モデルで代用し、2か所の `interrupt`（HITL①②）は
`Command(resume=...)` で自動再開してオフラインで完走する。

| ファイル | 対応節 | 内容 |
|---------|-------|------|
| `_common.py` | 11-4/11-6/11-7 | ダミーの3情報源（Web・CRM・過去案件）＋擬似モデル（計画立案・統合） |
| `11-2_new_features_minimal.py` | 11-2 | 新機能3つの最小デモ（ループ＋recursion_limit／ToolNode／interrupt） |
| `11-3_agent_pipeline.py` | 11-3〜11-7 | Planner→HITL①→Executor(ループ＋ToolNode)→Synthesizer→HITL②→出力の全体版 |
| `11-4_planner_hitl.py` | 11-4 | Planner＋HITL①。承認／修正して承認／却下の3通りを実演 |
| `11-5_executor_loop.py` | 11-5 | Executor・再帰エッジのループ・ToolNodeで計画を消化 |

本番では、Web検索は既製のWeb検索MCP（Tavily等）、CRMは公式のCRM MCP
（Salesforce/HubSpot等・利用者本人の権限で接続）、過去案件は自社ログのRAG（第3章）に、
擬似モデルは実際のモデル呼び出しに置き換わる（本文どおり）。

## 動作確認バージョン

- Python 3.10 以上（langgraph は Python>=3.10。実行確認は 3.12）
- langgraph 1.x / langchain-core 0.3.x（`requirements.txt`）

> **バージョンは固定する**
>
> LangGraph まわりは更新が速い。本書で使う最小の書き方（`StateGraph`／`add_node`／
> `add_conditional_edges`／`compile`／`ToolNode`／`interrupt`／`Command`）は安定して
> いるが、本番では依存版を固定すること。`ToolNode`・`tools_condition` は
> `langgraph.prebuilt` から取り出す。

## 実行

### セットアップ

```bash
cd samples
python3 -m venv .venv
source .venv/bin/activate        # Windows は .venv\Scripts\activate
pip install -r requirements.txt
```

### ドライラン（APIキー・ネットワーク不要）

```bash
python 11-2_new_features_minimal.py
python 11-4_planner_hitl.py
python 11-5_executor_loop.py
python 11-3_agent_pipeline.py
```

## 期待される出力（抜粋）

### `11-3_agent_pipeline.py`

```text
=== 計画承認 → ドラフト承認（正常系）===
  HITL①一時停止: 計画 = ['みらい物流の直近ニュースをWebで調べる', ...]
  HITL②一時停止: ドラフト = みらい物流、2026年に新倉庫を稼働。...
  --- 商談準備ドキュメント（承認済み）---
  準備メモ: ...
=== 計画を却下（実行に進まないことを確認）===
  → 却下のため計画を立て直して終了（実行には進まない）
```

計画を承認した場合だけ実行〜統合〜最終レビューに進み、却下すると実行に進まない。
2か所のHITLが構造としての関門になっていることが確認できる（本文 11-4・11-7）。
