"""12-3 文書レビュー補助エージェント ── 全体パイプライン（オフライン）

本文 12-3〜12-6 を1本につないだ完全版。
  Supervisor（振り分け）→ 3観点のWorkerを【並列】実行（法務／業務要件／技術妥当性）
                        → 結果を reducer で集約 → Supervisor（統合レポート生成）→ 出力

アーキテクチャは Supervisor-Worker のハイブリッド：
  - Supervisor層 = LangGraph（振り分け・並列制御・統合）
  - Worker層     = Claude Agent SDK（各観点の深い分析）… 本サンプルでは擬似Workerで代用

APIキー・ネットワーク不要。各Workerは擬似分析（_common.py）、統合は擬似モデルで代用し、
3観点を並列に走らせて統合レポートを作るところまでをオフラインで完走する。
本番では、各Workerの中身を Claude Agent SDK の query() 呼び出しに置き換える（本文どおり）。
"""

from __future__ import annotations

import operator
from typing import Annotated
from typing_extensions import TypedDict

from langgraph.graph import END, START, StateGraph

from _common import numbered_document, pseudo_worker_analyze, pseudo_integrate


class State(TypedDict, total=False):
    document: list          # レビュー対象の文書（行番号つき）
    findings: Annotated[list, operator.add]  # 各Workerの指摘（並列なので reducer で集約）
    report: str             # 統合レポート


# --- Supervisor層：振り分け（12-4）------------------------------------------
VIEWPOINTS = ["法務", "業務要件", "技術妥当性"]


def supervisor_dispatch(state: State):
    # 文書を受け取り、レビュー観点を決める（ここでは3観点で固定）。副作用なし
    return {}


def route_to_workers(state: State):
    # 3観点のWorkerへ同時に分岐（fan-out）。返したノードは並列に実行される
    return ["legal_worker", "requirements_worker", "tech_worker"]


# --- Worker層：各観点の分析（12-5）------------------------------------------
# 本番では各Workerの中身が Claude Agent SDK の query() 呼び出しになる。
def legal_worker(state: State):
    return {"findings": pseudo_worker_analyze("法務", state["document"])}


def requirements_worker(state: State):
    return {"findings": pseudo_worker_analyze("業務要件", state["document"])}


def tech_worker(state: State):
    return {"findings": pseudo_worker_analyze("技術妥当性", state["document"])}


# --- Supervisor層：統合（12-6）----------------------------------------------
def integrate(state: State):
    # fan-in：3Workerがすべて終わってから1回だけ動く。指摘は reducer で集約済み
    return {"report": pseudo_integrate(state["findings"])}


def build_graph():
    b = StateGraph(State)
    b.add_node("supervisor", supervisor_dispatch)
    b.add_node("legal_worker", legal_worker)
    b.add_node("requirements_worker", requirements_worker)
    b.add_node("tech_worker", tech_worker)
    b.add_node("integrate", integrate)

    b.add_edge(START, "supervisor")
    # Supervisor → 3Worker へ fan-out（並列）
    b.add_conditional_edges("supervisor", route_to_workers,
                            ["legal_worker", "requirements_worker", "tech_worker"])
    # 3Worker → integrate へ集約（LangGraph が全Workerの完了を自動で待つ＝fan-in）
    b.add_edge("legal_worker", "integrate")
    b.add_edge("requirements_worker", "integrate")
    b.add_edge("tech_worker", "integrate")
    b.add_edge("integrate", END)
    return b.compile()


def main():
    graph = build_graph()
    out = graph.invoke({"document": numbered_document(), "findings": []},
                       {"recursion_limit": 50})
    print("=== 3観点を並列レビューして統合 ===")
    print(f"  集まった指摘の総数: {len(out['findings'])}件（3観点ぶん）")
    print()
    print(out["report"])


if __name__ == "__main__":
    main()
