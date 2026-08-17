"""11-6 横断ハイブリッド検索をSubgraphに組む ── 完全版（オフライン）

本文 11-6 の骨格を動かす。前半で検索の各段（ベクトル検索＋キーワード検索→
RRF統合→リランキング）の順位を確かめ、後半でそれを本文どおり Subgraph
（11-4 の形）に組み立てて実行する。APIキー・ネットワーク不要。

実運用では、各ソースへの問い合わせは 11-5 の自作MCPサーバー経由になり、埋め込みは本物の
埋め込みモデル、リランキングは専用リランカーに置き換わる（第3章3-5）。
この Subgraph を親グラフに add_node で載せた全体版は 11-2_agent_pipeline.py。
"""

from __future__ import annotations

from typing import TypedDict

from langgraph.graph import StateGraph, START, END

from _common import vector_search, keyword_search, hybrid_search, rerank

QUESTION = "先月の障害対応の記録と、その後のデプロイ手順は？"


# --- 検索Subgraph（本文11-6のコードの完全形）----------------------------------
# 本文は「主張が読める骨格」だけを載せている。ここが実際に動く実体。
class State(TypedDict, total=False):
    question: str
    retrieved: list


def search_sources(state: State):
    # 各ソースの自前インデックス（本番は11-5の自作MCP経由）に問い合わせ、候補を集める。
    # 各文書には権限メタデータ（部署・機密区分など）を必ず持たせる（本文11-6）。
    # ダミーコーパスの hybrid_search が「ベクトル＋キーワード→RRF統合」まで担う。
    return {"retrieved": hybrid_search(state["question"])}


def rerank_node(state: State):
    # 集めた候補を、質問との関連度で並べ直し、上位だけ残す
    return {"retrieved": rerank(state["question"], state["retrieved"], top=3)}


def build_search_subgraph():
    # 組み立ては11-4と同型：「集める」→「精査する」をつないでコンパイルし、
    # 親グラフの add_node にそのまま渡せる「部品」にする
    b = StateGraph(State)
    b.add_node("search_sources", search_sources)
    b.add_node("rerank", rerank_node)
    b.add_edge(START, "search_sources")
    b.add_edge("search_sources", "rerank")
    b.add_edge("rerank", END)
    return b.compile()


def main() -> None:
    print(f"[質問] {QUESTION}\n")

    # --- 前半：検索の各段の順位を確かめる（第3章3-5の実戦投入）---------------
    v = vector_search(QUESTION)
    print("[ベクトル検索の順位]", [d["id"] for d in v])

    k = keyword_search(QUESTION)
    print("[キーワード検索の順位]", [d["id"] for d in k])

    fused = hybrid_search(QUESTION)
    print("[RRFで統合した順位]", [d["id"] for d in fused])

    top = rerank(QUESTION, fused, top=3)
    print("[リランキング後の上位3件]", [d["id"] for d in top])

    # --- 後半：同じ処理をSubgraphとして実行する（本文11-6）--------------------
    subgraph = build_search_subgraph()
    result = subgraph.invoke({"question": QUESTION})
    print("\n[Subgraphとして実行した結果]", [d["id"] for d in result["retrieved"]])
    print("上位の中身:")
    for d in result["retrieved"]:
        print(f"  - {d['id']}（{d['source']}）: {d['excerpt']}")


if __name__ == "__main__":
    main()
