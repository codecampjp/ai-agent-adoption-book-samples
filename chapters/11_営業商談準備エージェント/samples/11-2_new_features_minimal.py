"""11-2 本章で新しく使う3機能の最小デモ ── ループ・ToolNode・interrupt

本文 11-2 で概念を押さえた3つの機能を、それぞれ独立した最小例で動かして確かめる。
LLM もネットワークも不要（interrupt は Command(resume=...) で自動再開する）。
"""

from __future__ import annotations

from typing import Annotated
from typing_extensions import TypedDict

from langchain_core.messages import AIMessage
from langchain_core.tools import tool
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langgraph.types import Command, interrupt


# === (1) ループ：再帰エッジ＋recursion_limit ==================================
class CountState(TypedDict):
    n: int


def step(state: CountState):
    return {"n": state["n"] + 1}


def route(state: CountState):
    # 終了条件を満たすまで step へ戻る（＝再帰エッジでループ）
    return "step" if state["n"] < 3 else END


def demo_loop():
    b = StateGraph(CountState)
    b.add_node("step", step)
    b.add_edge(START, "step")
    b.add_conditional_edges("step", route, {"step": "step", END: END})
    graph = b.compile()
    # recursion_limit で暴走を防ぐ（上限を超えると GraphRecursionError）
    result = graph.invoke({"n": 0}, {"recursion_limit": 10})
    print("(1) ループ: n =", result["n"], "（3回まわって停止）")


# === (2) ToolNode：モデルが要求した道具を実行する ============================
@tool
def web_search(query: str) -> str:
    """Webを検索して要約を返す（デモ用のダミー）"""
    return f"『{query}』の検索結果（ダミー）"


class ToolState(TypedDict):
    messages: Annotated[list, add_messages]


def demo_toolnode():
    # ToolNode は「グラフのノード」として置いて使う（本文どおり）
    b = StateGraph(ToolState)
    b.add_node("tools", ToolNode([web_search]))
    b.add_edge(START, "tools")
    b.add_edge("tools", END)
    graph = b.compile()
    # モデルが「web_search を呼んで」と要求したと仮定した AIMessage を流す
    ai = AIMessage(content="", tool_calls=[
        {"name": "web_search", "args": {"query": "みらい物流 最新ニュース"}, "id": "call-1"},
    ])
    out = graph.invoke({"messages": [ai]})
    print("(2) ToolNode:", out["messages"][-1].content)


# === (3) interrupt：止めて、人間の判断で再開する =============================
class ApprovalState(TypedDict):
    messages: Annotated[list, add_messages]
    approved: bool


def ask_human(state: ApprovalState):
    decision = interrupt("この計画で進めてよいですか？")  # ここで停止
    return {"approved": bool(decision)}


def demo_interrupt():
    b = StateGraph(ApprovalState)
    b.add_node("ask_human", ask_human)
    b.add_edge(START, "ask_human")
    b.add_edge("ask_human", END)
    graph = b.compile(checkpointer=InMemorySaver())  # interrupt には checkpointer が必須

    config = {"configurable": {"thread_id": "t-1"}}
    paused = graph.invoke({"messages": []}, config)
    print("(3) interrupt: 一時停止 →", paused["__interrupt__"][0].value)
    # 人間の承認（True）を渡して再開。resume の値が interrupt() の戻り値になる
    resumed = graph.invoke(Command(resume=True), config)
    print("    再開 → approved =", resumed["approved"])


if __name__ == "__main__":
    demo_loop()
    demo_toolnode()
    demo_interrupt()
