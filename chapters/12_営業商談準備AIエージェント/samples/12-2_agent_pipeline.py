"""12-2 営業商談準備エージェント ── 全体パイプライン（オフライン）

本文12-2〜12-7を1本につないだ完全版。
  Planner → リスク判定 → 必要時だけHITL① → Executor（ToolNode＋二重ループ）
          → Synthesizer → HITL②（最終レビュー）→ finalize（承認後に初めて出力）

APIキー・ネットワーク不要。検索は擬似データ、計画・統合は擬似モデル、
条件付きHITLと必須の最終HITLはCommand(resume=...)で自動再開して完走する。
本番では、擬似モデルを実モデル呼び出しに、ダミー情報源を各検索ツールに置き換える。

ループは本文12-5のとおり二重になっている。
  小さなループ：executor →（ツール呼び出しあり）→ tools → executor（モデルが結果を確認）
  大きなループ：advance →（計画に残りあり）→ executor（次のステップへ＝再帰エッジ）
"""

from __future__ import annotations

from typing import Annotated
from typing_extensions import TypedDict

from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.tools import tool
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.types import Command, interrupt

from _common import (
    crm_lookup,
    past_case_lookup,
    plan_review_reasons,
    pseudo_plan,
    pseudo_synthesize,
    web_lookup,
)


# --- 3つの情報源（12-6）------------------------------------------------------
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
    plan_review_reasons: list[str]
    step_idx: int
    findings: list
    draft: dict
    approved_plan: bool
    approved_draft: bool
    messages: Annotated[list, add_messages]


# --- Planner ＋ HITL①（12-3・12-4）-----------------------------------------
def planner(state: State):
    plan = pseudo_plan(state["goal"])
    return {
        "plan": plan,
        "plan_review_reasons": plan_review_reasons(state["goal"], plan),
        "step_idx": 0,
        "findings": [],
    }


def route_after_planner(state: State):
    return "review_plan" if state["plan_review_reasons"] else "executor"


def review_plan(state: State):
    decision = interrupt({
        "reasons": state["plan_review_reasons"],
        "plan": [s["desc"] for s in state["plan"]],
        "ask": "不足条件を補うか、この計画で進めるか判断してください",
    })
    if decision.get("edited_plan"):
        # 修正後の計画もステップの形（desc/tool/arg）を保っている前提
        return {"plan": decision["edited_plan"], "approved_plan": True}
    return {"approved_plan": decision.get("approved", False)}


def route_after_plan(state: State):
    return "executor" if state.get("approved_plan") else "replan"


def replan(state: State):
    # 却下されたら計画を立て直す（本サンプルでは同じ計画を再提示して終える）
    return {"plan": pseudo_plan(state["goal"]), "approved_plan": False}


# --- Executor（ToolNode＋二重ループ）（12-5）--------------------------------
def executor(state: State):
    step = state["plan"][state["step_idx"]]
    # 擬似モデル：直前がツールの結果（ToolMessage）なら「このステップは調べ終えた」と
    # 判断してツールなしの返答を返し、まだならツールの呼び出しを要求する。
    # 本番では model_with_tools.invoke(...) がこの判断ごと担う（本文12-5）
    last = state["messages"][-1] if state.get("messages") else None
    if isinstance(last, ToolMessage):
        return {"messages": [AIMessage(content=f"ステップ{state['step_idx'] + 1}の調査を終えた")]}
    ai = AIMessage(content="", tool_calls=[
        {"name": step["tool"], "args": {"query": step["arg"]}, "id": f"call-{state['step_idx']}"},
    ])
    return {"messages": [ai]}


def route_executor(state: State):
    # モデルの最後の返答にツール呼び出しが残っていれば、ツールを実行しにいく（小さなループ）
    if tools_condition(state) == "tools":
        return "tools"
    # ツールを使い終えたステップの結果を畳んで、次へ
    return "advance"


def advance(state: State):
    # いまのステップのツールの結果（最後の ToolMessage）を findings に積み、ステップを進める
    step = state["plan"][state["step_idx"]]
    result = next(m.content for m in reversed(state["messages"])
                  if isinstance(m, ToolMessage))
    finding = {"tool": step["tool"], "result": result}
    return {"findings": state["findings"] + [finding], "step_idx": state["step_idx"] + 1}


def route_after_advance(state: State):
    # 計画にまだ残りがあれば executor へ戻る（大きなループ＝再帰エッジ）、なければ統合へ
    return "executor" if state["step_idx"] < len(state["plan"]) else "synthesizer"


# --- Synthesizer ＋ HITL②（12-7）-------------------------------------------
def synthesizer(state: State):
    return {"draft": pseudo_synthesize(state["goal"], state["findings"])}


def review_draft(state: State):
    decision = interrupt({"draft": state["draft"], "ask": "この内容で出してよいですか？"})
    if decision.get("edited_draft"):
        return {"draft": decision["edited_draft"], "approved_draft": True}
    return {"approved_draft": decision.get("approved", False)}


def route_after_review(state: State):
    # レビューを通ったドラフトだけが finalize（外に出す）へ進める
    return "finalize" if state.get("approved_draft") else "withhold"


def withhold(state: State):
    # 却下されたドラフトは外に出さない（本サンプルでは差し戻して終える）
    print("  → 却下のため出力しない（ドラフトは外に出ていない）")
    return {}


def finalize(state: State):
    # レビューを通ったドラフトだけが、ここで初めて外向きの出力になる
    d = state["draft"]
    print("  --- 商談準備ドキュメント（承認済み）---")
    print("  準備メモ:", d["準備メモ"])
    print("  想定質問:", d["想定質問"])
    print("  確認したい質問:", d["確認したい質問"])
    print("  提案骨子:", d["提案骨子"])
    print("  未確認事項と出典:", d["未確認事項と出典"])
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
    b.add_node("withhold", withhold)
    b.add_node("finalize", finalize)

    b.add_edge(START, "planner")
    b.add_conditional_edges("planner", route_after_planner,
                            {"review_plan": "review_plan", "executor": "executor"})
    b.add_conditional_edges("review_plan", route_after_plan,
                            {"executor": "executor", "replan": "replan"})
    b.add_edge("replan", END)
    b.add_conditional_edges("executor", route_executor,
                            {"tools": "tools", "advance": "advance"})
    b.add_edge("tools", "executor")                    # ツールの後はモデルへ戻る（小さなループ）
    b.add_conditional_edges("advance", route_after_advance,
                            {"executor": "executor", "synthesizer": "synthesizer"})
    b.add_edge("synthesizer", "review_draft")
    b.add_conditional_edges("review_draft", route_after_review,
                            {"finalize": "finalize", "withhold": "withhold"})
    b.add_edge("withhold", END)
    b.add_edge("finalize", END)
    return b.compile(checkpointer=InMemorySaver())


def run(
    label: str,
    thread_id: str,
    goal: str,
    plan_decision: dict | None,
    draft_decision: dict | None,
):
    graph = build_graph()
    config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 50}
    print(f"\n=== {label} ===")

    # 1) 通常はHITL①を通らず、リスクがある計画だけHITL①で停止
    paused = graph.invoke({"goal": goal}, config)
    payload = paused["__interrupt__"][0].value
    if "plan" in payload:
        print("  HITL①一時停止理由:", payload["reasons"])
        print("  計画への判断:", plan_decision)
        paused = graph.invoke(Command(resume=plan_decision), config)
        if "__interrupt__" not in paused:
            print("  → 却下のため計画を立て直して終了（実行には進まない）")
            return
    else:
        print("  → 確認理由なし。HITL①を挟まず自動実行")

    # 2) Synthesizer後は必ずHITL②で停止
    draft_payload = paused["__interrupt__"][0].value
    print("  HITL②一時停止: ドラフト =", draft_payload["draft"]["準備メモ"])
    print("  ドラフトへの判断:", draft_decision)

    # 3) 承認ならfinalizeで出力、却下なら外へ出さない
    graph.invoke(Command(resume=draft_decision), config)


def main():
    run("通常調査は自動実行 → ドラフト承認",
        "t-auto-ok", "みらい物流 新規提案", None, {"approved": True})
    run("曖昧な計画を確認して承認 → ドラフト承認",
        "t-risk-ok", "同名企業の可能性がある みらい物流 新規提案",
        {"approved": True}, {"approved": True})
    run("曖昧な計画を却下（実行に進まない）",
        "t-risk-reject", "同名企業の可能性がある みらい物流 新規提案",
        {"approved": False}, None)
    run("通常調査は自動実行 → ドラフト却下",
        "t-auto-reject", "みらい物流 新規提案", None, {"approved": False})


if __name__ == "__main__":
    main()
