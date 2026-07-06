"""7-2 StateGraph の全体像 ── 最小のグラフ

状態に1つの値を持ち、1つのノードを通すだけの最小例。
LLM もネットワークも不要で、そのまま実行できる。

本文 7-2 の掲載コードに対応する完全版。
"""

from typing_extensions import TypedDict

from langgraph.graph import END, START, StateGraph


# (1) 状態の形を決める（ここでは1つの文字列を持つだけ）
class State(TypedDict):
    value: str


# (2) ノード＝状態を受け取り、更新分を返す関数
def my_node(state: State):
    return {"value": state["value"] + " された"}


def build_graph():
    # (3) グラフを組み立てる
    builder = StateGraph(State)
    builder.add_node("my_node", my_node)  # ノードを登録
    builder.add_edge(START, "my_node")    # 開始点から my_node へ
    builder.add_edge("my_node", END)      # my_node で終了
    # (4) コンパイルして実行できる形にする
    return builder.compile()


def main():
    graph = build_graph()
    result = graph.invoke({"value": "処理"})
    print(result)  # {'value': '処理 された'}


if __name__ == "__main__":
    main()
