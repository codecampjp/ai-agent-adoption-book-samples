"""7-5 手書き ReAct を LangGraph で書き直す ── 完全版

本文 7-5 では「構造（状態・ノード・エッジ・分岐・戻り線）」に集中するため、
モデルやツールの準備といった周辺コードを省いた骨格だけを掲載した。
このファイルはその省いた周辺コードを補い、そのまま動かせるようにしたもの。

APIキーなし（ドライラン）でも動く：在庫確認エージェントを模した FakeReActModel が、
「A-100 を確認 → 品切れ → B-200 を確認 → 在庫あり → 最終回答」という ReAct ループを
回す。本番モード（実際のモデルに自走させる）は README を参照。
"""

from __future__ import annotations

import os
from typing import Annotated

from typing_extensions import TypedDict

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages


# --- 状態（本文掲載） ------------------------------------------------------
class State(TypedDict):
    messages: Annotated[list, add_messages]


# --- 周辺コード：ツール本体（本文では省略） --------------------------------
# ダミー在庫。A-100=品切れ、B-200=在庫あり。
_STOCK = {"A-100": 0, "B-200": 15}


def get_stock(product_code: str) -> int:
    return _STOCK.get(product_code, 0)


def execute_tool_calls(ai_message: AIMessage) -> list[ToolMessage]:
    """直前のモデル応答が要求した道具を実行し、tool_result を返す。"""
    results: list[ToolMessage] = []
    for call in ai_message.tool_calls:
        if call["name"] == "get_stock":
            value = get_stock(call["args"]["product_code"])
            results.append(ToolMessage(content=str(value), tool_call_id=call["id"]))
        else:
            results.append(
                ToolMessage(content="unknown tool", tool_call_id=call["id"])
            )
    return results


# --- 周辺コード：モデル（本文では model.invoke として参照のみ） ------------
def build_model():
    """本番モード：APIキーがあれば LangChain 経由で実モデルを使う。

    無ければドライラン用の FakeReActModel を返す。
    """
    if os.getenv("ANTHROPIC_API_KEY"):
        try:
            from langchain.chat_models import init_chat_model

            model = init_chat_model("claude-sonnet-4-6", model_provider="anthropic")
            from langchain_core.tools import tool

            @tool
            def get_stock_tool(product_code: str) -> str:
                """商品コードの在庫数を返す。"""
                return str(get_stock(product_code))

            return model.bind_tools([get_stock_tool]), True
        except Exception as exc:  # noqa: BLE001
            print(f"[メモ] 実モデルの初期化に失敗したためドライランに切替: {exc}")
    return FakeReActModel(), False


class FakeReActModel:
    """ドライラン用の擬似モデル。会話の進み具合を見て tool_use / 最終回答を返す。"""

    def invoke(self, messages):
        asked = {
            tm.tool_call_id
            for tm in messages
            if isinstance(tm, ToolMessage)
        }
        if "call-a" not in asked:
            return AIMessage(
                content="",
                tool_calls=[
                    {"name": "get_stock", "args": {"product_code": "A-100"}, "id": "call-a"}
                ],
            )
        if "call-b" not in asked:
            return AIMessage(
                content="",
                tool_calls=[
                    {"name": "get_stock", "args": {"product_code": "B-200"}, "id": "call-b"}
                ],
            )
        return AIMessage(
            content="商品A-100は品切れですが、代替品B-200が15個あります。"
        )


# --- ノードとエッジ（本文掲載） --------------------------------------------
def call_model(state: State):
    response = model.invoke(state["messages"])  # 道具を渡したモデルに問い合わせる
    return {"messages": [response]}             # 応答を会話に追記


def run_tools(state: State):
    last = state["messages"][-1]                # 直前のモデル応答
    results = execute_tool_calls(last)          # 要求された道具を実行
    return {"messages": results}                # 実行結果を会話に追記


def should_continue(state: State):
    last = state["messages"][-1]
    if last.tool_calls:                         # モデルが道具の使用を要求しているか
        return "tools"
    return END


def build_graph():
    builder = StateGraph(State)
    builder.add_node("model", call_model)
    builder.add_node("tools", run_tools)
    builder.add_edge(START, "model")                         # 開始 → モデル
    builder.add_conditional_edges("model", should_continue)  # モデルの後、分岐
    builder.add_edge("tools", "model")                       # ツールの後、モデルへ戻る（＝ループ）
    return builder.compile()


model, real_mode = build_model()


def main():
    if not real_mode:
        print("[メモ] ANTHROPIC_API_KEY 未設定のため、擬似モデルで流れだけを表示します。\n")
    graph = build_graph()
    question = "商品A-100の在庫を確認して。品切れなら代替品B-200の在庫も調べて、まとめて報告して。"
    result = graph.invoke(
        {"messages": [HumanMessage(content=question)]},
        {"recursion_limit": 25},
    )
    for m in result["messages"]:
        kind = type(m).__name__
        text = m.content if m.content else f"tool_calls={getattr(m, 'tool_calls', None)}"
        print(f"[{kind}] {text}")


if __name__ == "__main__":
    main()
