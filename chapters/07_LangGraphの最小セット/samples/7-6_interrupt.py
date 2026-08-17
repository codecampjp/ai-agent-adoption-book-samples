"""7-6 interrupt：HITL の最小実装 ── 完全版

本文 7-6 では interrupt を呼ぶノード（概念の核）だけを掲載した。
このファイルは、その続き（thread_id を指定して実行 → interrupt で止まる →
Command(resume=値) で再開）を実際に動かして確かめられるようにしたもの。
往復の流れは run_once() 上のトレース解説コメントと README を参照（本文から移設）。

LLM もネットワークも不要。承認（True）と却下（False）の両方を実演する。
"""

from __future__ import annotations

from typing_extensions import TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt


class State(TypedDict):
    amount: int
    approved: bool


# 承認を求めるノード（本文の概念コードと同じ）
def approval_node(state: State):
    # ここで実行が止まり、payload（質問文）が呼び出し側に渡される
    approved = interrupt(f"{state['amount']}円の決済を承認しますか？")
    # 再開すると、Command(resume=...) で渡した値が approved に入る
    return {"approved": approved}


# 承認結果に応じて副作用（決済）を実行するノード。
# interrupt は再開時にノードを「頭から」やり直すため、副作用は承認後の別ノードに置く（本文 7-6 の注意点）。
def execute_node(state: State):
    if state["approved"]:
        print(f"    → 決済を実行しました（{state['amount']}円）")
    else:
        print("    → 却下されたので何もしません")
    return {}


def build_graph():
    builder = StateGraph(State)
    builder.add_node("approval", approval_node)
    builder.add_node("execute", execute_node)
    builder.add_edge(START, "approval")
    builder.add_edge("approval", "execute")
    builder.add_edge("execute", END)
    # interrupt で止めた状態を保存するため、チェックポインターが必須（Checkpoint が土台）
    return builder.compile(checkpointer=InMemorySaver())


# 往復の流れ（トレース解説：本文 7-6 から移設）:
#   1回目の invoke: START → approval ノード → interrupt(...) で一時停止。
#                   このとき現在の状態がチェックポインターに保存され、
#                   payload（質問文）が戻り値の result["__interrupt__"] に入る
#   （人間が payload を見て判断する。何分後でも翌日でもよい——状態は保存済み）
#   2回目の invoke: 同じ thread_id で Command(resume=判断) を渡す
#                   → approval ノードが「頭から」再実行され、interrupt() が resume の値を返す
#                   → {"approved": 値} が黒板に書かれ、execute ノードへ進む
def run_once(thread_id: str, resume_value: bool):
    graph = build_graph()
    config = {"configurable": {"thread_id": thread_id}}

    # 1回目：approval_node の interrupt で止まる
    result = graph.invoke({"amount": 10000}, config)
    payload = result["__interrupt__"][0].value
    print(f"  一時停止: 「{payload}」")

    # 人間が判断したら、その値を渡して再開する（resume の値が interrupt() の戻り値になる）
    decision = "承認" if resume_value else "却下"
    print(f"  人間の判断: {decision} → Command(resume={resume_value}) で再開")
    graph.invoke(Command(resume=resume_value), config)


def main():
    print("[承認するケース]")
    run_once("t-approve", True)
    print("\n[却下するケース]")
    run_once("t-reject", False)


if __name__ == "__main__":
    main()
