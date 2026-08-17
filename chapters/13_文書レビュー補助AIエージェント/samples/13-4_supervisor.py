"""13-4 Supervisor層（LangGraph）── 振り分けと並列fan-out

本文13-4に対応。Supervisorが観点を決めて複数のWorkerへ並列に振り分け、
結果を reducer で集約するところを、Worker を軽いスタブにして単体で確かめる。
（Workerの分析は13-5、全体版は13-2を参照）

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
    # 文書を読み、レビューの観点を決める（ここでは3観点で固定）
    print("  Supervisor: 観点を振り分け →", list(WORKERS))
    return {}


def make_worker(viewpoint: str):
    # 各観点のWorker（13-5で中身をClaude Agent SDKに差し替える）のスタブ
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
    for worker in WORKERS.values():
        b.add_edge("supervisor", worker)
        b.add_edge(worker, "integrate")
    b.add_edge("integrate", END)
    return b.compile()


if __name__ == "__main__":
    print("=== Supervisorが3観点へ並列fan-out ===")
    out = build_graph().invoke({"document": "（契約書のダミー）", "findings": []})
    print("  最終の指摘数:", len(out["findings"]), "件（3観点が並列で埋めた）")
