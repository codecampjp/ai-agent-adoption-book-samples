"""10-2 Subgraph の最小例 ── 完全版（オフライン）

本文 10-2 の骨格を動かす。検索処理のかたまりを Subgraph（子グラフ）として
compile() し、親グラフの add_node にそのまま渡す（親と子で State のキーを共有）。
LLM もネットワークも使わない。検索はダミーコーパス（_common.py）で代用。
"""

from __future__ import annotations

from typing import TypedDict

from langgraph.graph import StateGraph, START, END

from _common import hybrid_search, rerank


class State(TypedDict, total=False):
    question: str
    retrieved: list
    answer: str


# --- 検索Subgraph（中は2つのノード）------------------------------------------
def search_sources(state: State):
    return {"retrieved": hybrid_search(state["question"])}


def rerank_node(state: State):
    return {"retrieved": rerank(state["question"], state["retrieved"], top=3)}


def build_search_subgraph():
    b = StateGraph(State)
    b.add_node("search_sources", search_sources)
    b.add_node("rerank", rerank_node)
    b.add_edge(START, "search_sources")
    b.add_edge("search_sources", "rerank")
    b.add_edge("rerank", END)
    return b.compile()   # ← これが「部品」になる


# --- 親グラフ：Subgraph を1つのノードとして置く ------------------------------
def answer(state: State):
    ids = [d["id"] for d in state["retrieved"]]
    return {"answer": f"関連文書 {ids} をもとに回答します。"}


def build_graph():
    search_subgraph = build_search_subgraph()
    parent = StateGraph(State)
    parent.add_node("search", search_subgraph)   # ← Subgraphをノードとして登録
    parent.add_node("answer", answer)
    parent.add_edge(START, "search")
    parent.add_edge("search", "answer")
    parent.add_edge("answer", END)
    return parent.compile()


def main() -> None:
    graph = build_graph()
    result = graph.invoke({"question": "障害対応の記録とデプロイ手順は？"})
    print("[取り出した文書]", [d["id"] for d in result["retrieved"]])
    print("[回答]", result["answer"])


if __name__ == "__main__":
    main()
