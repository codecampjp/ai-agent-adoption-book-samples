# 第10章 サンプルコード（権限制御つき社内ナレッジ横断エージェント）

本書 第10章の掲載コードを、そのまま実行できる形にまとめたもの。
ファイル名の先頭は対応する節番号（例 `10-5_` = 10-5節）。

本文では「どこがSubgraphで、どこで権限を絞り、どこで引用を付けているか」という
**構造**に集中するため、動かすための周辺コードを省いて骨格だけを掲載している。
ここではその周辺コードを補い、実際に動かせるようにしている。

すべて **APIキー・ネットワーク不要のドライラン**で動く。回答生成は本物のLLMの
代わりに擬似モデル、検索はダミーの社内コーパス（`_common.py`）で代用する。
`10-4` の複数MCP接続だけは、ローカルのダミーMCPサーバー（`mcp_servers/`）を
stdio で起動して、本物と同じ経路（MultiServerMCPClient）を確かめる。

| ファイル | 対応節 | 内容 |
|---------|-------|------|
| `_common.py` | 10-5/10-6 | ダミー社内コーパス＋ハイブリッド検索・RRF・リランキング・権限判定（共通部品） |
| `10-2_subgraph_minimal.py` | 10-2 | 検索処理をSubgraphに切り出し、親グラフのノードとして置く最小例 |
| `10-3_agent_pipeline.py` | 10-3〜10-7 | 検索Subgraph→権限チェック＋Conditional Edge→回答＋引用付与を1本につないだ全体版 |
| `10-4_multi_mcp.py` | 10-4 | MultiServerMCPClient で2つのローカルMCPサーバー（`mcp_servers/`）を束ねて横断検索 |
| `10-5_hybrid_search.py` | 10-5 | ベクトル検索＋キーワード検索→RRF統合→リランキングの順位を表示 |
| `10-6_permission_filter.py` | 10-6 | 権限フィルタ＋Conditional Edge。利用者ごとに見える文書が変わることを確認 |

本番では、検索は各データソースのMCPサーバー（10-4）へ、擬似モデルは実際のモデル
呼び出しへ、権限判定（`can_view`）は自社の認可基盤へ置き換わる（本文どおり）。

## 動作確認バージョン

- Python 3.10 以上（実行確認は 3.12）
- langgraph 1.x / langchain-mcp-adapters 0.3.x / fastmcp 3.x（`requirements.txt`）

> **バージョンは固定する**
>
> LangGraph・MCP まわりは更新が速い。本書で使う最小の書き方（`StateGraph`／
> `add_node`／`add_conditional_edges`／`compile`／`MultiServerMCPClient`）は
> 安定しているが、本番では依存版を固定すること。

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
python 10-5_hybrid_search.py
python 10-2_subgraph_minimal.py
python 10-6_permission_filter.py
python 10-3_agent_pipeline.py
python 10-4_multi_mcp.py
```

## 期待される出力（抜粋）

### `10-6_permission_filter.py`

```text
[一般の開発者] 質問『給与テーブルはどこ？』 → 見えた文書=[]
           回答: 該当する情報は見つかりませんでした。
[人事部員] 質問『給与テーブルはどこ？』 → 見えた文書=['doc-SP-9012']
           回答: 閲覧可能な文書 ['doc-SP-9012'] をもとに回答します。
```

一般の開発者には人事限定の給与文書が見えず、人事部員には見える。権限フィルタが
確定的に効いていることが確認できる（本文 10-6）。

### `10-4_multi_mcp.py`

```text
[取得したツール] ['confluence_search', 'github_search']
[confluence_search] -> ...
[github_search] -> ...
```

2つのMCPサーバーのツールが1つのクライアントにまとまり、横断して呼べる（本文 10-4）。
