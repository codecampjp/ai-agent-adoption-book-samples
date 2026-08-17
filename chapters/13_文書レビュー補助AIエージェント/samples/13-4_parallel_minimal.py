"""13-4 並列処理の最小デモ ── fan-out・reducerでのfan-in・Send

本文13-4のfan-out、リデューサ、Sendを独立した最小例で確かめる。
LLMもネットワークも不要。

(1) fan-out（複数行き先）＋reducerでのfan-in：1ノードから複数ノードへ同時に分岐し、
    並列に走らせて、結果を1つの状態にマージする。
(2) Send API：分岐数を実行時に決める動的な並列（map-reduce）。
"""

from __future__ import annotations

import operator
from typing import Annotated
from typing_extensions import TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import Send


# === (1) fan-out＋reducerでのfan-in =========================================
# 状態キー results に reducer（operator.add）を付けると、並列に走った各ノードの
# 返り値が「上書き」ではなく「足し合わせ」で集まる（reducerが無いと後勝ちで消える）。
class FanState(TypedDict):
    results: Annotated[list, operator.add]


def worker_a(state: FanState):
    return {"results": ["Aの結果"]}


def worker_b(state: FanState):
    return {"results": ["Bの結果"]}


def worker_c(state: FanState):
    return {"results": ["Cの結果"]}


def gather(state: FanState):
    # fan-in：3つの並列ノードがすべて終わってから、ここが1回だけ動く
    return {}


def demo_fanout():
    b = StateGraph(FanState)
    for name, fn in [("worker_a", worker_a), ("worker_b", worker_b),
                     ("worker_c", worker_c), ("gather", gather)]:
        b.add_node(name, fn)
    # 接続先が固定なら、通常のエッジを複数張って並列化する
    b.add_edge(START, "worker_a")
    b.add_edge(START, "worker_b")
    b.add_edge(START, "worker_c")
    b.add_edge("worker_a", "gather")
    b.add_edge("worker_b", "gather")
    b.add_edge("worker_c", "gather")
    b.add_edge("gather", END)
    out = b.compile().invoke({"results": []})
    print("(1) fan-out＋reducer:", out["results"], "（並列の結果がマージされた）")


# === (2) Send API：分岐数を実行時に決める動的な並列 =========================
class MapState(TypedDict):
    items: list
    results: Annotated[list, operator.add]


def analyze_one(state: dict):
    # Send で渡された個別の状態（{"item": ...}）を受け取る
    return {"results": [f"{state['item']}を分析"]}


def route_to_items(state: MapState):
    # 項目の数だけ Send を作る＝いくつ並列に走らせるかを実行時に決める
    return [Send("analyze_one", {"item": it}) for it in state["items"]]


def demo_send():
    b = StateGraph(MapState)
    b.add_node("analyze_one", analyze_one)
    b.add_conditional_edges(START, route_to_items, ["analyze_one"])
    b.add_edge("analyze_one", END)
    out = b.compile().invoke({"items": ["法務", "業務要件", "技術妥当性"], "results": []})
    print("(2) Send API:", out["results"], "（項目数ぶん動的に並列）")


if __name__ == "__main__":
    demo_fanout()
    demo_send()
