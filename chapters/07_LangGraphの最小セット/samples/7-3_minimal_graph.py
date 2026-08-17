"""7-3 StateGraphで組む ── 最小のグラフ（完全版）

状態に1つの値を持ち、1つのノードを通すだけの最小例。
LLM もネットワークも不要で、そのまま実行できる。

本文 7-3 の掲載コードに対応する完全版。本文では「(1)状態の形を決める →
(2)ノードを登録する → (3)エッジでつなぐ → (4)コンパイルして実行する」という
4ステップの型だけを示した。ここでは各行が4ステップのどこにあたるかと、
invoke したときに何が起きるかをコメントで1行ずつ追う（本文から移設したトレース解説）。
"""

from typing_extensions import TypedDict

from langgraph.graph import END, START, StateGraph


# (1) 状態の形を決める
#     処理の途中で持ち回るデータ（共有の黒板）の構造。ここでは文字列1つだけ。
class State(TypedDict):
    value: str


# (2) ノード＝状態を受け取り、更新分を返す関数
#     黒板全体（state）を受け取り、「書き足したい分」だけを辞書で返す。
#     返さなかったキーは据え置かれる（このStateはキーが1つなので全部だが）。
def my_node(state: State):
    return {"value": state["value"] + " された"}


def build_graph():
    # (3) エッジでつなぐ（処理＝ノードと、流れ＝エッジを別々に登録する）
    builder = StateGraph(State)           # 状態の形を渡して入れ物を作る
    builder.add_node("my_node", my_node)  # ノードを登録（名前と関数のペア）
    builder.add_edge(START, "my_node")    # START（入口）→ my_node
    builder.add_edge("my_node", END)      # my_node → END（出口）
    # (4) コンパイルして実行できる形にする
    return builder.compile()


def main():
    graph = build_graph()
    # 実行の流れ（トレース）:
    #   invoke に初期状態 {"value": "処理"} を渡す
    #   → START から my_node へ進む
    #   → my_node が黒板を読み {"value": "処理 された"} を返す（更新分）
    #   → 更新分が黒板に反映され、エッジに従って END へ
    #   → 最終的な黒板の中身が戻り値になる
    result = graph.invoke({"value": "処理"})
    print(result)  # {'value': '処理 された'}


if __name__ == "__main__":
    main()
