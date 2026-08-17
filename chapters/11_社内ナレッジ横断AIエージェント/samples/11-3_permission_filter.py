"""11-3 権限チェックと Conditional Edge ── 完全版（オフライン）

本文 11-3 の骨格を動かす。確定的なコードで権限フィルタをかけ、見てよい文書が
1件も無ければ Conditional Edge で「見つかりません」経路へ振り分ける。
2人の利用者（一般の開発者／人事部員）で、同じ質問への結果の違いを確かめる。
"""

from __future__ import annotations

from typing import TypedDict

from langgraph.graph import StateGraph, START, END

from _common import hybrid_search, rerank, can_view


class State(TypedDict, total=False):
    question: str
    user: dict
    retrieved: list
    visible: list
    answer: str


def search(state: State):
    docs = rerank(state["question"], hybrid_search(state["question"]), top=5)
    return {"retrieved": docs}


def check_permission(state: State):
    user = state["user"]
    visible = [d for d in state["retrieved"] if can_view(user, d["meta"])]
    return {"visible": visible}


def route_after_permission(state: State):
    return "answer" if state["visible"] else "no_answer"


def answer(state: State):
    ids = [d["id"] for d in state["visible"]]
    return {"answer": f"閲覧可能な文書 {ids} をもとに回答します。"}


def no_answer(state: State):
    return {"answer": "該当する情報は見つかりませんでした。"}


def build_graph():
    b = StateGraph(State)
    b.add_node("search", search)
    b.add_node("check_permission", check_permission)
    b.add_node("answer", answer)
    b.add_node("no_answer", no_answer)
    b.add_edge(START, "search")
    b.add_edge("search", "check_permission")
    b.add_conditional_edges("check_permission", route_after_permission)
    b.add_edge("answer", END)
    b.add_edge("no_answer", END)
    return b.compile()


def main() -> None:
    graph = build_graph()
    users = {
        "一般の開発者": {"dept": "dev", "clearance": 1},
        "人事部員": {"dept": "hr", "clearance": 3},
    }
    for label, user in users.items():
        q = "給与テーブルはどこ？"
        result = graph.invoke({"question": q, "user": user})
        seen = [d["id"] for d in result["visible"]]
        print(f"[{label}] 質問『{q}』 → 見えた文書={seen}")
        print(f"           回答: {result['answer']}")


if __name__ == "__main__":
    main()
