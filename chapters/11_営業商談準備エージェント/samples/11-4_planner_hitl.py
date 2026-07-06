"""11-4 Planner と HITL① ── 計画を立て、人間が承認・修正する（オフライン）

本文 11-4 の骨格を動かす。Planner が調査計画を立て、review_plan の interrupt で
止まり、Command(resume=...) で人間の判断（承認／修正して承認／却下）を返して再開する。
却下なら replan へ、承認なら（本サンプルでは）計画を表示して終了する。

LLM もネットワークも不要。3通りの判断を自動で実演する。
"""

from __future__ import annotations

from typing_extensions import TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from _common import pseudo_plan


class State(TypedDict, total=False):
    goal: str
    plan: list
    step_idx: int
    approved_plan: bool


def planner(state: State):
    # 計画を立てるだけ（副作用なし）。実運用ではこの並びをモデルが作る
    return {"plan": pseudo_plan(state["goal"]), "step_idx": 0}


def review_plan(state: State):
    # 計画を人間に見せて、ここで止まる（HITL①）。副作用は置かない
    decision = interrupt({"plan": [s["desc"] for s in state["plan"]],
                          "ask": "この調査計画で進めてよいですか？"})
    if decision.get("edited_plan"):
        return {"plan": decision["edited_plan"], "approved_plan": True}
    return {"approved_plan": decision.get("approved", False)}


def route_after_plan(state: State):
    return "executor" if state.get("approved_plan") else "replan"


def executor(state: State):
    print("    → 承認された計画を実行へ:", [s["desc"] if isinstance(s, dict) else s
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
    b.add_edge("planner", "review_plan")
    b.add_conditional_edges("review_plan", route_after_plan,
                            {"executor": "executor", "replan": "replan"})
    b.add_edge("executor", END)
    b.add_edge("replan", END)
    return b.compile(checkpointer=InMemorySaver())


def run(label: str, thread_id: str, resume_value: dict):
    graph = build_graph()
    config = {"configurable": {"thread_id": thread_id}}
    paused = graph.invoke({"goal": "みらい物流 新規提案"}, config)
    print(f"\n=== {label} ===")
    print("  一時停止: 計画 =", paused["__interrupt__"][0].value["plan"])
    print("  人間の判断:", resume_value)
    graph.invoke(Command(resume=resume_value), config)


def main():
    run("そのまま承認", "t-approve", {"approved": True})
    run("修正して承認", "t-edit", {"edited_plan": ["まず失注理由を再確認する", "代替の料金体系を検討する"]})
    run("却下", "t-reject", {"approved": False})


if __name__ == "__main__":
    main()
