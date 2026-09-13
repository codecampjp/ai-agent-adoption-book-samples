"""13-2 文書レビュー補助エージェント ── 全体パイプライン（オフライン）

本文13-2〜13-6を1本につないだ完全版。
  Supervisor（振り分け）→ 3観点のWorkerを【並列】実行（法務／業務要件／技術妥当性）
                        → 結果を reducer で集約 → 参照の実在を検証（validate_findings）
                        → Supervisor（統合レポート生成）→ 出力

デモとして、実在しない条項を指す「でっち上げの指摘」を最初から1件混ぜてある。
検証ノードがそれを「根拠不一致」として分け、統合レポートに明示する（本文13-6）。

アーキテクチャは Supervisor-Worker のハイブリッド：
  - Supervisor層 = LangGraph（振り分け・並列制御・統合）
  - Worker層     = Claude Agent SDK（各観点の深い分析）… 本サンプルでは擬似Workerで代用

APIキー・ネットワーク不要。各Workerは擬似分析（_common.py）、統合は擬似モデルで代用し、
3観点を並列に走らせて統合レポートを作るところまでをオフラインで完走する。
本番では、各Workerの中身をClaude Agent SDKのquery()呼び出しに置き換える。
"""

from __future__ import annotations

import operator
from typing import Annotated
from typing_extensions import TypedDict

from langgraph.graph import END, START, StateGraph

from _common import (numbered_document, pseudo_worker_analyze, pseudo_integrate,
                     validate_findings)


class State(TypedDict, total=False):
    document: list          # レビュー対象の文書（行番号つき）
    findings: Annotated[list, operator.add]  # 各Workerの指摘（並列なので reducer で集約）
    worker_errors: Annotated[list, operator.add]  # 失敗した観点（指摘0件とは別）
    valid_findings: list    # 検証（参照の実在チェック）を通った指摘だけ
    rejected_findings: list # 検証で弾かれた指摘（実在しない章・行・抜粋を指すもの）
    report: str             # 統合レポート


# --- Supervisor層：振り分け（13-4）------------------------------------------
VIEWPOINTS = ["法務", "業務要件", "技術妥当性"]


def supervisor_dispatch(state: State):
    # 文書を受け取り、レビュー観点を決める（ここでは3観点で固定）
    return {}


# --- Worker層：各観点の分析（13-5）------------------------------------------
# 本番では各Workerの中身が Claude Agent SDK の query() 呼び出しになる。
def legal_worker(state: State):
    return {"findings": pseudo_worker_analyze("法務", state["document"])}


def requirements_worker(state: State):
    return {"findings": pseudo_worker_analyze("業務要件", state["document"])}


def tech_worker(state: State):
    return {"findings": pseudo_worker_analyze("技術妥当性", state["document"])}


# --- 検証：参照を入力文書へ照合（13-6）---------------------------------------
def validate(state: State):
    # fan-in：3Workerがすべて終わってから1回だけ動く。指摘は reducer で集約済み。
    # 文書ID・版・章・行・抜粋を原文と突き合わせ、根拠不一致を分ける
    valid, rejected = validate_findings(state["findings"], state["document"])
    return {"valid_findings": valid, "rejected_findings": rejected}


# --- Supervisor層：統合（13-6）----------------------------------------------
def integrate(state: State):
    # 有効な指摘に加え、根拠不一致も未確認事項としてレポートに残す
    return {"report": pseudo_integrate(
        state["valid_findings"],
        state["rejected_findings"],
        state.get("worker_errors", []),
    )}


def build_graph():
    b = StateGraph(State)
    b.add_node("supervisor", supervisor_dispatch)
    b.add_node("legal_worker", legal_worker)
    b.add_node("requirements_worker", requirements_worker)
    b.add_node("tech_worker", tech_worker)
    b.add_node("validate", validate)
    b.add_node("integrate", integrate)

    b.add_edge(START, "supervisor")
    # 接続先が固定なので、通常のエッジで3Workerを並列化する
    b.add_edge("supervisor", "legal_worker")
    b.add_edge("supervisor", "requirements_worker")
    b.add_edge("supervisor", "tech_worker")
    b.add_edge("legal_worker", "validate")
    b.add_edge("requirements_worker", "validate")
    b.add_edge("tech_worker", "validate")
    b.add_edge("validate", "integrate")
    b.add_edge("integrate", END)
    return b.compile()


# 検証デモ用：実在しない条項を指す「でっち上げの指摘」（第99条は文書に無い）
FABRICATED = {
    "document_id": "contract-demo", "document_version": "v1",
    "viewpoint": "法務", "chapter": "第99条(存在しない)", "line": 99,
    "excerpt": "この条文は文書に存在しない。", "issue": "でっち上げの指摘（検証デモ用）",
    "severity": "高", "recommendation": "原文を確認する。", "status": "根拠未確認",
}


def main():
    graph = build_graph()
    out = graph.invoke({"document": numbered_document(), "findings": [FABRICATED]},
                       {"recursion_limit": 50})
    print("=== 3観点を並列レビューして統合 ===")
    print(f"  集まった指摘の総数: {len(out['findings'])}件"
          f"（3観点ぶん＋デモ用のでっち上げ1件）")
    print(f"  根拠不一致の指摘: {len(out['rejected_findings'])}件"
          f" → {[f['chapter'] for f in out['rejected_findings']]}")
    print(f"  根拠を確認できた指摘: {len(out['valid_findings'])}件")
    print()
    print(out["report"])


if __name__ == "__main__":
    main()
