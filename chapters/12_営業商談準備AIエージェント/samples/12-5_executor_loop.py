"""12-5 Executor・ループ・ToolNode ── 計画をステップごとに実行する（オフライン）

本文12-5の骨格を動かす。ループは本文どおり二重になっている。
  小さなループ：executor →（ツール呼び出しあり）→ tools → executor（モデルが結果を確認）
  大きなループ：advance →（計画に残りあり）→ executor（次のステップへ＝再帰エッジ）

擬似モデルは「ツールの結果がまだ無ければツールを1つ呼び、結果を見たらそのステップを
終える」決め打ちにして、LLM 無しでループの構造だけを確かめられるようにしている
（本番ではモデルがツールと引数を選び、足りなければ続けてツールを呼ぶ）。
"""

from __future__ import annotations

import json

from typing import Annotated
from typing_extensions import TypedDict

from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.tools import tool
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition

from _common import pseudo_plan, search_result, decode_result


# --- 3つの情報源をツールにする（12-6）---------------------------------------
@tool
def web_search(query: str) -> str:
    """公開Web情報を検索する"""
    return json.dumps(search_result("web_search", query), ensure_ascii=False)


@tool
def crm_search(query: str) -> str:
    """社内CRMを利用者の権限内で検索する"""
    return json.dumps(search_result("crm_search", query), ensure_ascii=False)


@tool
def past_case_search(query: str) -> str:
    """過去案件ログ（自社RAG）を検索する"""
    return json.dumps(search_result("past_case_search", query), ensure_ascii=False)


TOOLS = [web_search, crm_search, past_case_search]


class State(TypedDict, total=False):
    goal: str
    plan: list
    step_idx: int
    findings: list
    messages: Annotated[list, add_messages]


def planner(state: State):
    return {"plan": pseudo_plan(state["goal"]), "step_idx": 0, "findings": []}


def executor(state: State):
    step = state["plan"][state["step_idx"]]
    # 擬似モデル：直前がツールの結果（ToolMessage）なら「このステップは調べ終えた」と
    # 判断してツールなしの返答を返し、まだならツールの呼び出しを要求する
    last = state["messages"][-1] if state.get("messages") else None
    if isinstance(last, ToolMessage):
        return {"messages": [AIMessage(content=f"ステップ{state['step_idx'] + 1}の調査を終えた")]}
    ai = AIMessage(content="", tool_calls=[
        {"name": step["tool"], "args": {"query": step["arg"]}, "id": f"call-{state['step_idx']}"},
    ])
    return {"messages": [ai]}


def route_executor(state: State):
    # ツール呼び出しが残っていれば tools へ（小さなループ）、使い終えたら advance へ
    if tools_condition(state) == "tools":
        return "tools"
    return "advance"


def advance(state: State):
    # いまのステップのツールの結果（最後の ToolMessage）を findings に積み、ステップを進める
    step = state["plan"][state["step_idx"]]
    result = next(m.content for m in reversed(state["messages"])
                  if isinstance(m, ToolMessage))
    finding = {"tool": step["tool"], "result": decode_result(result)}
    return {"findings": state["findings"] + [finding], "step_idx": state["step_idx"] + 1}


def route_after_advance(state: State):
    # 残りのステップがあれば executor へ戻る（大きなループ＝再帰エッジ）、なければ終了
    return "executor" if state["step_idx"] < len(state["plan"]) else END


def build_graph():
    b = StateGraph(State)
    b.add_node("planner", planner)
    b.add_node("executor", executor)
    b.add_node("tools", ToolNode(TOOLS))
    b.add_node("advance", advance)
    b.add_edge(START, "planner")
    b.add_edge("planner", "executor")
    b.add_conditional_edges("executor", route_executor,
                            {"tools": "tools", "advance": "advance"})
    b.add_edge("tools", "executor")                    # ツールの後はモデルへ戻る（小さなループ）
    b.add_conditional_edges("advance", route_after_advance,
                            {"executor": "executor", END: END})
    return b.compile()


def main():
    graph = build_graph()
    result = graph.invoke({"goal": "みらい物流 新規提案"}, {"recursion_limit": 50})
    print("=== 計画を消化した結果（findings）===")
    for f in result["findings"]:
        print(f"  [{f['tool']}] {f['result']}")


if __name__ == "__main__":
    main()
