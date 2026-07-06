"""12-4 Supervisor層（LangGraph）── 振り分けと並列fan-out

本文 12-4 に対応。Supervisor が観点を決めて複数のWorkerへ【並列】に振り分け、
結果を reducer で集約するところを、Worker を軽いスタブにして単体で確かめる。
（Worker の中身＝各観点の深い分析は 12-5、全体版は 12-3 を参照）

APIキー・ネットワーク不要。
"""

from __future__ import annotations

import operator
from typing import Annotated
from typing_extensions import TypedDict

from langgraph.graph import END, START, StateGraph


class State(TypedDict, total=False):
    document: str
    findings: Annotated[list, operator.add]  # 並列Workerの結果を足し合わせて集約


# 観点（表示名）→ Workerノード名。ノード名に日本語や記号（: 等）は使えないので分ける
WORKERS = {"法務": "legal_worker", "業務要件": "requirements_worker",
           "技術妥当性": "tech_worker"}


def supervisor(state: State):
    # 文書を読み、レビューの観点を決める（ここでは3観点で固定）。副作用は持たせない
    print("  Supervisor: 観点を振り分け →", list(WORKERS))
    return {}


def route_to_workers(state: State):
    # 観点の数だけWorkerノードへ同時分岐（fan-out）。返した先は並列に実行される
    return list(WORKERS.values())


def make_worker(viewpoint: str):
    # 各観点のWorker（12-5で中身を Claude Agent SDK に差し替える）のスタブ
    def worker(state: State):
        return {"findings": [{"viewpoint": viewpoint, "issue": f"{viewpoint}の指摘（ダミー）"}]}
    return worker


def integrate(state: State):
    # fan-in：全Workerの完了後に1回だけ動く
    print("  Integrate: 集約された指摘 =", [f["viewpoint"] for f in state["findings"]])
    return {}


def build_graph():
    b = StateGraph(State)
    b.add_node("supervisor", supervisor)
    for vp, node in WORKERS.items():
        b.add_node(node, make_worker(vp))
    b.add_node("integrate", integrate)

    b.add_edge(START, "supervisor")
    b.add_conditional_edges("supervisor", route_to_workers, list(WORKERS.values()))
    for node in WORKERS.values():
        b.add_edge(node, "integrate")
    b.add_edge("integrate", END)
    return b.compile()


if __name__ == "__main__":
    print("=== Supervisorが3観点へ並列fan-out ===")
    out = build_graph().invoke({"document": "（契約書のダミー）", "findings": []})
    print("  最終の指摘数:", len(out["findings"]), "件（3観点が並列で埋めた）")
