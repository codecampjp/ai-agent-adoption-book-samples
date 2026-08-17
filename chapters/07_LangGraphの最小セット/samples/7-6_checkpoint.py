"""7-6 Checkpoint：状態の永続化 ── 完全版

本文 7-6 では「(1) コンパイル時にチェックポインターを渡す／(2) 実行時に thread_id を
指定する」という骨格だけを掲載した。このファイルは、その続き（同じ thread_id で
呼ぶと前回の会話を覚えている／別の thread_id ならまっさらから始まる）を
実際に動かして確かめられるようにしたもの。実行の流れは README も参照。

LLM もネットワークも不要。respond ノードは過去の会話（state["messages"]）を全部
読めるので、「チェックポインターのおかげで状態が持ち回られている」ことが確認できる。
"""

from __future__ import annotations

import re
from typing import Annotated

from typing_extensions import TypedDict

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages


class State(TypedDict):
    messages: Annotated[list, add_messages]


def respond(state: State):
    """直近の発言に応答する。過去の全メッセージを参照できる点がポイント。"""
    text = state["messages"][-1].content
    # これまでの会話から名前を拾う（状態が永続化されているから過去も見える）
    name = None
    for m in state["messages"]:
        hit = re.search(r"私は(.+?)です", getattr(m, "content", "") or "")
        if hit:
            name = hit.group(1)
    if "名前" in text:
        reply = f"あなたの名前は{name}です。" if name else "まだ名前を教わっていません。"
    else:
        reply = "こんにちは。"
    return {"messages": [AIMessage(content=reply)]}


def build_graph():
    builder = StateGraph(State)
    builder.add_node("respond", respond)
    builder.add_edge(START, "respond")
    builder.add_edge("respond", END)
    # ★ (1) コンパイル時にチェックポインターを渡す（本文の概念コードと同じ）
    return builder.compile(checkpointer=InMemorySaver())


def say(graph, config, text):
    out = graph.invoke({"messages": [HumanMessage(content=text)]}, config)
    print(f"  user> {text}")
    print(f"  bot > {out['messages'][-1].content}")


# 実行の流れ（トレース解説：本文 7-6 から移設）:
#   1回目の invoke（thread-1）: まっさらな黒板に「私はボブです」が積まれ、節目で保存される
#   2回目の invoke（thread-1）: 同じ thread_id → 保存済みの黒板が復元され、
#                               respond ノードは過去の発言から「ボブ」を見つけられる
#   3回目の invoke（thread-2）: 別の thread_id → 別の黒板。過去の会話は見えない
def main():
    graph = build_graph()

    # ★ (2) 実行時に thread_id を指定する。同じIDなら前回の状態（会話）を覚えている
    config = {"configurable": {"thread_id": "thread-1"}}
    print("[thread-1]")
    say(graph, config, "こんにちは、私はボブです。")
    say(graph, config, "私の名前は何でしたか？")  # → ボブ と答えられる

    # 別の thread_id はまっさらな状態から始まる
    config2 = {"configurable": {"thread_id": "thread-2"}}
    print("\n[thread-2]（別スレッド＝記憶なし）")
    say(graph, config2, "私の名前は何でしたか？")  # → 教わっていない


if __name__ == "__main__":
    main()
