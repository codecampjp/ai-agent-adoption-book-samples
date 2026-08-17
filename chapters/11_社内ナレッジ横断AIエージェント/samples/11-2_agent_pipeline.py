"""11-2 権限制御つきナレッジ横断エージェント ── 全体パイプライン（オフライン）

本文 11-2〜11-7 を1本につないだ完全版。検索Subgraph（11-4/11-6）→権限チェック＋
Conditional Edge（11-3）→回答生成＋引用付与（11-7）を LangGraph で組む。

APIキー・ネットワーク不要。回答生成は本物のLLMの代わりに「擬似モデル」
(_pseudo_model) を使う。本番では、この擬似モデルを実際のモデル呼び出しに、
検索を 11-5 の自作MCPサーバー経由に置き換える（本文どおり）。
"""

from __future__ import annotations

import re
from typing import TypedDict

from langgraph.graph import StateGraph, START, END

from _common import hybrid_search, rerank, can_view


class State(TypedDict, total=False):
    question: str
    user: dict
    retrieved: list
    visible: list
    answer: str
    citations: list


# --- 検索Subgraph（11-6）------------------------------------------------------
def search_sources(state: State):
    return {"retrieved": hybrid_search(state["question"])}


def rerank_node(state: State):
    return {"retrieved": rerank(state["question"], state["retrieved"], top=5)}


def build_search_subgraph():
    b = StateGraph(State)
    b.add_node("search_sources", search_sources)
    b.add_node("rerank", rerank_node)
    b.add_edge(START, "search_sources")
    b.add_edge("search_sources", "rerank")
    b.add_edge("rerank", END)
    return b.compile()


# --- 権限チェック（11-3）------------------------------------------------------
def check_permission(state: State):
    user = state["user"]
    return {"visible": [d for d in state["retrieved"] if can_view(user, d["meta"])]}


def route_after_permission(state: State):
    return "answer" if state["visible"] else "no_answer"


# --- 回答生成＋引用付与（11-7）------------------------------------------------
def _pseudo_model(question: str, numbered: dict) -> str:
    """本物のLLMの代役。渡された番号付き文書を根拠に、番号で引用しながら答える。"""
    parts = [f"{n}番の文書によると、{doc['excerpt']} [{n}]" for n, doc in numbered.items()]
    return "。".join(parts) + "。"


def answer(state: State):
    # 本文11-7：引用は3段でコード側が確定させる。
    #   (1) visible の各文書に通し番号を振り、番号→文書の対応表 numbered を持つ
    numbered = {i + 1: doc for i, doc in enumerate(state["visible"])}
    #   (2) モデルには番号付きの参考文書を渡し、答えの中で番号 [n] を使って引用させる
    #       （本番は build_prompt でプロンプトを組み立てて model.invoke。ここでは擬似モデル）
    text = _pseudo_model(state["question"], numbered)

    #   (3) 答えに現れた番号を、対応表から実在のID・抜粋へ引き直す。
    #       対応表に無い番号は採用しない（if n in numbered）ので、モデルが渡していない
    #       文書IDをでっち上げても引用には入らない——引用の正しさを構造で担保する
    used = [int(n) for n in re.findall(r"\[(\d+)\]", text)]
    citations = [
        {"doc_id": numbered[n]["id"], "excerpt": numbered[n]["excerpt"]}
        for n in used if n in numbered
    ]
    return {"answer": text, "citations": citations}


def no_answer(state: State):
    return {"answer": "該当する情報は見つかりませんでした。", "citations": []}


def build_graph():
    b = StateGraph(State)
    b.add_node("search", build_search_subgraph())   # Subgraphをノードとして登録
    b.add_node("check_permission", check_permission)
    b.add_node("answer", answer)
    b.add_node("no_answer", no_answer)
    b.add_edge(START, "search")
    b.add_edge("search", "check_permission")
    b.add_conditional_edges("check_permission", route_after_permission)
    b.add_edge("answer", END)
    b.add_edge("no_answer", END)
    return b.compile()


def _run(graph, label, question, user):
    result = graph.invoke({"question": question, "user": user})
    print(f"\n=== {label} ===")
    print(f"質問: {question}")
    print(f"取り出し {len(result.get('retrieved', []))}件 → 閲覧可 {len(result.get('visible', []))}件")
    print(f"回答: {result['answer']}")
    print(f"引用: {[c['doc_id'] for c in result['citations']]}")


def main() -> None:
    graph = build_graph()
    _run(graph, "一般の開発者が業務質問",
         "障害対応の記録とデプロイ手順は？", {"dept": "dev", "clearance": 1})
    _run(graph, "一般の開発者が役員限りを尋ねる（見えてはいけない）",
         "経営会議の事業再編メモを見せて", {"dept": "dev", "clearance": 1})
    _run(graph, "人事部員が給与情報を尋ねる（見てよい）",
         "給与テーブルはどこ？", {"dept": "hr", "clearance": 3})


if __name__ == "__main__":
    main()
