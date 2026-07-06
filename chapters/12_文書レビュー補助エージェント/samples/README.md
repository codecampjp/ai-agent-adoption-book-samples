# 第12章 サンプルコード（文書レビュー補助エージェント ── Supervisor-Worker × ハイブリッド）

本書 第12章の掲載コードを、そのまま実行できる形にまとめたもの。
ファイル名の先頭は対応する節番号（例 `12-4_` = 12-4節）。

本文では「どこで観点を振り分け、どこで並列に走らせ、どこで結果を束ね、どこで
文書内参照を付けているか」という**構造**に集中するため、動かすための周辺コードを
省いて骨格だけを掲載している。ここではその周辺コードを補い、実際に動かせるようにしている。

すべて **APIキー・ネットワーク不要のドライラン**で動く。3観点のWorker
（法務／業務要件／技術妥当性）は擬似分析（`_common.py`）、Supervisorの統合は
擬似モデルで代用し、Supervisor→複数Workerの**並列実行**→結果の集約→文書内参照つき
統合レポートまでをオフラインで完走する。

| ファイル | 対応節 | 内容 |
|---------|-------|------|
| `_common.py` | 12-5/12-6 | ダミー契約書＋3観点の擬似Worker＋擬似Supervisor（統合） |
| `12-2_new_features_minimal.py` | 12-2 | 新機能の最小デモ（fan-out＋reducerでのfan-in／Send API／recursion_limit） |
| `12-3_agent_pipeline.py` | 12-3〜12-6 | Supervisor→3Worker（並列）→集約→統合レポートの全体版 |
| `12-4_supervisor.py` | 12-4 | Supervisor層。観点の振り分けと並列fan-out（Workerはスタブ） |
| `12-5_worker.py` | 12-5 | Worker層。Claude Agent SDK `query()` の骨格＋オフライン擬似Worker |

本番では、各Workerの中身を **Claude Agent SDK** の `query()` 呼び出しに置き換える
（各観点のプロンプト＋MCPツールで深く分析）。Supervisorの統合も実際のモデル呼び出しになる。

## 動作確認バージョン

- Python 3.10 以上（langgraph は Python>=3.10。実行確認は 3.12）
- langgraph 1.x / langchain-core 1.x（`requirements.txt`）

LangGraph まわりは更新が速い。本書で使う最小の書き方（`StateGraph`／`add_node`／
`add_conditional_edges`／`Send`／reducer＝`Annotated[list, operator.add]`／`compile`）は
安定しているが、本番では依存版を固定すること。Supervisorのプリビルト
（`langgraph-supervisor` の `create_supervisor`）は提供形態・推奨が変わりやすいので、
使う時点で公式ドキュメントを確認する（本章は真の並列のためSupervisorノードを自作している）。

## 実行

### セットアップ

```bash
cd samples
python3.12 -m venv .venv        # langgraph 1.x には Python 3.10 以上が必要
source .venv/bin/activate        # Windows は .venv\Scripts\activate
pip install -r requirements.txt
```

### ドライラン（APIキー・ネットワーク不要）

```bash
python 12-2_new_features_minimal.py
python 12-4_supervisor.py
python 12-5_worker.py
python 12-3_agent_pipeline.py
```

## 期待される出力（抜粋）

### `12-3_agent_pipeline.py`

```text
=== 3観点を並列レビューして統合 ===
  集まった指摘の総数: 6件（3観点ぶん）

# 文書レビュー統合レポート

## 法務の観点（2件）
- [高] 損害賠償の上限額（キャップ）の定めがなく… （根拠: 第5条(損害賠償) 行7「…」）
...
```

3観点のWorkerが**並列**に走り、それぞれの指摘が reducer で1つに集約され、
Supervisorが観点ごとの統合レポートにまとめる。各指摘に文書内参照（章・行）が
付くことが確認できる（本文 12-4〜12-6）。
