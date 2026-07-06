"""11-3 営業商談準備エージェント ── 全体パイプライン（オフライン）

本文 11-3〜11-7 を1本につないだ完全版。
  Planner → HITL①（計画承認）→ Executor（ToolNode＋ループ）→ Synthesizer
          → HITL②（最終レビュー）→ finalize（承認後に初めて出力）

APIキー・ネットワーク不要。検索は擬似データ、計画・統合は擬似モデル、
2つの interrupt は Command(resume=...) で自動再開してオフラインで完走する。
本番では、擬似モデルを実モデル呼び出しに、道具を各MCP/自社RAGに置き換える（本文どおり）。
"""

from __future__ import annotations

from typing import Annotated
from typing_extensions import TypedDict

from langchain_core.messages import AIMessage
from langchain_core.tools import tool
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.types import Command, interrupt

from _common import pseudo_plan, pseudo_synthesize, web_lookup, crm_lookup, past_case_lookup


# --- 3つの情報源（11-6）------------------------------------------------------
@tool
def web_search(query: str) -> str:
    """公開Web情報を検索する"""
    return " / ".join(web_lookup(query)) or "（Web該当なし）"


@tool
def crm_search(query: str) -> str:
    """社内CRMを利用者の権限内で検索する"""
    return " / ".join(crm_lookup(query)) or "（CRM該当なし）"


@tool
def past_case_search(query: str) -> str:
    """過去案件ログ（自社RAG）を検索する"""
    hits = past_case_lookup(query)
    return " / ".join(f"[{c['id']}] {c['summary']}" for c in hits) or "（過去案件該当なし）"


TOOLS = [web_search, crm_search, past_case_search]


class State(TypedDict, total=False):
    goal: str
    plan: list
    step_idx: int
    findings: list
    draft: dict
    approved_plan: bool
    messages: Annotated[list, add_messages]


# --- Planner ＋ HITL①（11-4）------------------------------------------------
def planner(state: State):
    return {"plan": pseudo_plan(state["goal"]), "step_idx": 0, "findings": []}


def review_plan(state: State):
    decision = interrupt({"plan": [s["desc"] for s in state["plan"]],
                          "ask": "この調査計画で進めてよいですか？"})
    if decision.get("edited_plan"):
        return {"plan": decision["edited_plan"], "approved_plan": True}
    return {"approved_plan": decision.get("approved", False)}


def route_after_plan(state: State):
    return "executor" if state.get("approved_plan") else "replan"


def replan(state: State):
    # 却下されたら計画を立て直す（本サンプルでは同じ計画を再提示して終える）
    return {"plan": pseudo_plan(state["goal"]), "approved_plan": False}


# --- Executor（ToolNode＋ループ）（11-5）------------------------------------
def executor(state: State):
    step = state["plan"][state["step_idx"]]
    ai = AIMessage(content="", tool_calls=[
        {"name": step["tool"], "args": {"query": step["arg"]}, "id": f"call-{state['step_idx']}"},
    ])
    return {"messages": [ai]}


def advance(state: State):
    step = state["plan"][state["step_idx"]]
    finding = {"tool": step["tool"], "result": state["messages"][-1].content}
    return {"findings": state["findings"] + [finding], "step_idx": state["step_idx"] + 1}


def route_after_advance(state: State):
    return "executor" if state["step_idx"] < len(state["plan"]) else "synthesizer"


# --- Synthesizer ＋ HITL②（11-7）-------------------------------------------
def synthesizer(state: State):
    return {"draft": pseudo_synthesize(state["goal"], state["findings"])}


def review_draft(state: State):
    decision = interrupt({"draft": state["draft"], "ask": "この内容で出してよいですか？"})
    if decision.get("edited_draft"):
        return {"draft": decision["edited_draft"]}
    return {}


def finalize(state: State):
    # レビューを通ったドラフトだけが、ここで初めて外向きの出力になる（副作用）
    d = state["draft"]
    print("  --- 商談準備ドキュメント（承認済み）---")
    print("  準備メモ:", d["準備メモ"])
    print("  想定質問:", d["想定質問"])
    print("  提案骨子:", d["提案骨子"])
    return {}


def build_graph():
    b = StateGraph(State)
    b.add_node("planner", planner)
    b.add_node("review_plan", review_plan)
    b.add_node("replan", replan)
    b.add_node("executor", executor)
    b.add_node("tools", ToolNode(TOOLS))
    b.add_node("advance", advance)
    b.add_node("synthesizer", synthesizer)
    b.add_node("review_draft", review_draft)
    b.add_node("finalize", finalize)

    b.add_edge(START, "planner")
    b.add_edge("planner", "review_plan")
    b.add_conditional_edges("review_plan", route_after_plan,
                            {"executor": "executor", "replan": "replan"})
    b.add_edge("replan", END)
    b.add_conditional_edges("executor", tools_condition)
    b.add_edge("tools", "advance")
    b.add_conditional_edges("advance", route_after_advance,
                            {"executor": "executor", "synthesizer": "synthesizer"})
    b.add_edge("synthesizer", "review_draft")
    b.add_edge("review_draft", "finalize")
    b.add_edge("finalize", END)
    return b.compile(checkpointer=InMemorySaver())


def run(label: str, thread_id: str, plan_decision: dict, draft_decision: dict | None):
    graph = build_graph()
    config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 50}
    print(f"\n=== {label} ===")

    # 1) Planner の後、HITL① で停止
    paused = graph.invoke({"goal": "みらい物流 新規提案"}, config)
    print("  HITL①一時停止: 計画 =", paused["__interrupt__"][0].value["plan"])
    print("  計画への判断:", plan_decision)

    # 2) 計画の判断を返して再開 → 却下なら replan で終了、承認なら実行〜Synthesizer後の HITL②で停止
    resumed = graph.invoke(Command(resume=plan_decision), config)
    if "__interrupt__" not in resumed:
        print("  → 却下のため計画を立て直して終了（実行には進まない）")
        return
    print("  HITL②一時停止: ドラフト =", resumed["__interrupt__"][0].value["draft"]["準備メモ"])
    print("  ドラフトへの判断:", draft_decision)

    # 3) ドラフトの判断を返して再開 → finalize で出力
    graph.invoke(Command(resume=draft_decision), config)


def main():
    run("計画承認 → ドラフト承認（正常系）",
        "t-ok", {"approved": True}, {"approved": True})
    run("計画を却下（実行に進まないことを確認）",
        "t-reject", {"approved": False}, None)


if __name__ == "__main__":
    main()
