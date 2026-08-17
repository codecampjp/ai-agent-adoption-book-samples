"""interrupt 応用：標準入力で人間の承認を待つ版（本サンプルリポジトリ限定の追加教材）。

※ このファイルは書籍本文には登場しない。リポジトリ独自の追加教材である。

7-6_interrupt.py は承認（True）／却下（False）を自動で連続実演する学習用だった。
このファイルは、interrupt で止まったあとに実際にキーボード入力を待ち、
その判断で再開する「人間が承認を挟む」流れ（本文 7-6 の HITL）を体感できるようにしたもの。

LLM もネットワークも不要。決済金額を入力 → 承認待ちで止まる →
[y/N] の入力で再開、という HITL の最小ループを回す。

実行:
    python interactive_interrupt.py

終了: 金額の入力で空行を入れるか、Ctrl+C（または Ctrl+D）。
"""

from __future__ import annotations

import argparse

from typing_extensions import TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt


class State(TypedDict):
    amount: int
    approved: bool


# 承認を求めるノード（本文 7-6 の概念コードと同じ）
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
    # interrupt で止めた状態を保存するため、チェックポインターが必須（本文 7-6 の Checkpoint が土台）
    return builder.compile(checkpointer=InMemorySaver())


def ask_human(payload: str) -> bool:
    """interrupt の質問を表示し、標準入力で承認/却下を受け取る。"""
    while True:
        answer = input(f"  {payload} [y/N]: ").strip().lower()
        if answer in ("y", "yes"):
            return True
        if answer in ("", "n", "no"):
            return False
        print("  y か n で答えてください。")


def run_once(thread_id: str, amount: int):
    graph = build_graph()
    config = {"configurable": {"thread_id": thread_id}}

    # 1回目：approval_node の interrupt で止まる
    result = graph.invoke({"amount": amount}, config)
    payload = result["__interrupt__"][0].value

    # ここで実際に人間の入力を待つ（interrupt の戻り値になる値を集める）
    resume_value = ask_human(payload)

    # 人間が判断したら、その値を渡して再開する（resume の値が interrupt() の戻り値になる）
    decision = "承認" if resume_value else "却下"
    print(f"  人間の判断: {decision} → Command(resume={resume_value}) で再開")
    graph.invoke(Command(resume=resume_value), config)


def main():
    parser = argparse.ArgumentParser(
        description=(
            "interrupt で止まったグラフを、キーボード入力（承認/却下）で再開する "
            "HITL の対話デモ。本サンプルリポジトリ限定の追加教材（書籍本文には登場しない）。"
        )
    )
    parser.parse_args()

    print("決済の承認フローです（空行または Ctrl+C で終了）。\n")
    counter = 0
    while True:
        try:
            raw = input("決済金額を入力してください（円）: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not raw:
            break
        if not raw.isdigit():
            print("  数字で入力してください。\n")
            continue

        counter += 1
        # thread_id は実行ごとに変える（同じ id だと完了済みスレッドを再利用してしまう）
        try:
            run_once(f"t-{counter}", int(raw))
        except (EOFError, KeyboardInterrupt):
            print("\n[メモ] 承認待ちを中断しました。")
            break
        print()


if __name__ == "__main__":
    main()
