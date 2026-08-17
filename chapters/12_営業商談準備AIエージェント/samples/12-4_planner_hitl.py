"""12-4 Planner と条件付きHITL ── リスクがある計画だけ人間へ確認する（オフライン）

本文12-3・12-4の骨格を動かす。Plannerの後で確認理由を判定し、通常の参照調査は
Executorへ自動で進める。対象が曖昧な場合だけreview_planのinterruptで止まり、
Command(resume=...)で人間の判断（承認／却下）を返して再開する。

LLMもネットワークも不要。自動実行、確認後の承認、確認後の却下を実演する。
"""

from __future__ import annotations

from typing_extensions import TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from _common import plan_review_reasons, pseudo_plan


class State(TypedDict, total=False):
    goal: str
    plan: list
    plan_review_reasons: list[str]
    step_idx: int
    approved_plan: bool


def planner(state: State):
    # 計画を立てるだけで、外部システムは変更しない。実運用ではこの並びをモデルが作る
    plan = pseudo_plan(state["goal"])
    return {
        "plan": plan,
        "plan_review_reasons": plan_review_reasons(state["goal"], plan),
        "step_idx": 0,
    }


def route_after_planner(state: State):
    return "review_plan" if state["plan_review_reasons"] else "executor"


def review_plan(state: State):
    # 確認理由と計画を人間に見せて止まる。更新・保存・送信は置かない
    decision = interrupt({
        "reasons": state["plan_review_reasons"],
        "plan": [s["desc"] for s in state["plan"]],
        "ask": "不足条件を補うか、この計画で進めるか判断してください",
    })
    if decision.get("edited_plan"):
        return {"plan": decision["edited_plan"], "approved_plan": True}
    return {"approved_plan": decision.get("approved", False)}


def route_after_plan(state: State):
    return "executor" if state.get("approved_plan") else "replan"


def executor(state: State):
    print("    → 確定した計画を実行へ:", [s["desc"] if isinstance(s, dict) else s
                                        for s in state["plan"]])
    return {}


def replan(state: State):
    print("    → 却下されたので計画を立て直す")
    return {}


def build_graph():
    b = StateGraph(State)
    b.add_node("planner", planner)
    b.add_node("review_plan", review_plan)
    b.add_node("executor", executor)
    b.add_node("replan", replan)
    b.add_edge(START, "planner")
    b.add_conditional_edges("planner", route_after_planner,
                            {"review_plan": "review_plan", "executor": "executor"})
    b.add_conditional_edges("review_plan", route_after_plan,
                            {"executor": "executor", "replan": "replan"})
    b.add_edge("executor", END)
    b.add_edge("replan", END)
    return b.compile(checkpointer=InMemorySaver())


def run(label: str, thread_id: str, goal: str, resume_value: dict | None = None):
    graph = build_graph()
    config = {"configurable": {"thread_id": thread_id}}
    print(f"\n=== {label} ===")
    paused = graph.invoke({"goal": goal}, config)
    if "__interrupt__" not in paused:
        print("  → 確認理由なし。HITLを挟まず自動実行")
        return
    payload = paused["__interrupt__"][0].value
    print("  一時停止理由:", payload["reasons"])
    print("  計画:", payload["plan"])
    print("  人間の判断:", resume_value)
    graph.invoke(Command(resume=resume_value), config)


def main():
    run("通常の参照調査", "t-auto", "みらい物流 新規提案")
    run("対象が曖昧な計画を確認して承認", "t-approve",
        "同名企業の可能性がある みらい物流 新規提案", {"approved": True})
    run("対象が曖昧な計画を却下", "t-reject",
        "同名企業の可能性がある みらい物流 新規提案", {"approved": False})


if __name__ == "__main__":
    main()
