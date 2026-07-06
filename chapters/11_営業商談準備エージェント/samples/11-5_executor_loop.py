"""11-5 Executor・ループ・ToolNode ── 計画をステップごとに実行する（オフライン）

本文 11-5 の骨格を動かす。ToolNode で3つの道具（Web・CRM・過去案件）を実行し、
実行ノードから戻る再帰エッジで計画を1ステップずつ消化する。残りが無くなったら抜ける。

擬似モデルは「いまのステップに対応する道具を1つ呼ぶ」決め打ちにして、LLM 無しで
ループの構造だけを確かめられるようにしている（本番ではモデルが道具と引数を選ぶ）。
"""

from __future__ import annotations

from typing import Annotated
from typing_extensions import TypedDict

from langchain_core.messages import AIMessage
from langchain_core.tools import tool
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition

from _common import pseudo_plan, web_lookup, crm_lookup, past_case_lookup


# --- 3つの情報源を道具にする（11-6）-----------------------------------------
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
_TOOLS_BY_NAME = {t.name: t for t in TOOLS}


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
    # 擬似モデル：いまのステップに対応する道具を1つ要求する AIMessage を作る
    ai = AIMessage(content="", tool_calls=[
        {"name": step["tool"], "args": {"query": step["arg"]}, "id": f"call-{state['step_idx']}"},
    ])
    return {"messages": [ai]}


def advance(state: State):
    # いまのステップの道具の結果（直前の ToolMessage）を findings に積み、ステップを進める
    step = state["plan"][state["step_idx"]]
    last = state["messages"][-1].content
    finding = {"tool": step["tool"], "result": last}
    return {"findings": state["findings"] + [finding], "step_idx": state["step_idx"] + 1}


def route_after_advance(state: State):
    # 残りのステップがあれば executor へ戻る（再帰エッジ）、なければ終了
    return "executor" if state["step_idx"] < len(state["plan"]) else END


def build_graph():
    b = StateGraph(State)
    b.add_node("planner", planner)
    b.add_node("executor", executor)
    b.add_node("tools", ToolNode(TOOLS))
    b.add_node("advance", advance)
    b.add_edge(START, "planner")
    b.add_edge("planner", "executor")
    b.add_conditional_edges("executor", tools_condition)   # 道具呼び出しがあれば "tools" へ
    b.add_edge("tools", "advance")
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
