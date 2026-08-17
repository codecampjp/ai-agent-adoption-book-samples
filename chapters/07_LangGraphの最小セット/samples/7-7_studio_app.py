"""7-7 LangSmith Studio で可視化する ── 完全版（langgraph dev で開くアプリ）

本文 7-7 は、`langgraph dev` でローカルの開発サーバを立て、ブラウザで
LangSmith Studio（旧称 LangGraph Studio）を開くと、自分が組んだグラフが
ノードとエッジの図として表示される、という位置づけを説明した。
このファイルは、その Studio に映すための「可視化対象グラフ」を公開するアプリ本体。

本文の「前節までに組んだ『モデル→ツール→モデル』のループが、そのまま図になります」
に対応して、7-5 で組んだ ReAct ループのノード（モデル／ツール／分岐）をそのまま
可視化対象として公開する。

使い方（詳細は README の 7-7 節）:
    pip install -U "langgraph-cli[inmem]"
    langgraph dev              # 同じフォルダの langgraph.json を読んで開発サーバを起動
    # 起動時に表示される URL をブラウザで開くと、Studio にこのグラフが表示される

APIキーは不要。7-5 と同じく、ANTHROPIC_API_KEY があれば実モデル、なければ
擬似モデル（FakeReActModel）で動く。どちらでも Studio に映るグラフ構造は同じ。

このファイルを直接 `python 7-7_studio_app.py` で実行すると、Studio に映る前に
グラフ構造のプレビュー（Mermaid 記法）を標準出力に表示する（Studio が無くても
「どんな図になるか」を確かめられる）。
"""

from __future__ import annotations

import importlib
import os
import sys

from langgraph.graph import END, START, StateGraph

# 7-5 のノード（モデル／ツール／分岐）をそのまま再利用する。
# ファイル名が数字始まりで通常の import 文が書けないため importlib で読む。
# langgraph dev がどこから読み込んでもよいよう、このファイルの場所を import 経路に加える。
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
_react = importlib.import_module("7-5_react_graph")

State = _react.State
call_model = _react.call_model
run_tools = _react.run_tools
should_continue = _react.should_continue


def build_studio_graph():
    """7-5 と同じ ReAct ループを、可視化向けに組み直す。

    7-5 本文では `add_conditional_edges("model", should_continue)` と書いたが、
    Studio や draw_mermaid が「分岐の行き先」を図に描けるよう、ここでは
    行き先の対応（パスマップ）を明示する。返り値 "tools"→tools ノード、
    END→終了、という対応を渡すと、モデルからの分岐（tools へ／END へ）と
    tools→model の戻り線が図として現れる。挙動は 7-5 とまったく同じ。
    """
    builder = StateGraph(State)
    builder.add_node("model", call_model)
    builder.add_node("tools", run_tools)
    builder.add_edge(START, "model")
    builder.add_conditional_edges(
        "model",
        should_continue,
        {"tools": "tools", END: END},  # 分岐先を明示（可視化のため）
    )
    builder.add_edge("tools", "model")  # ツールの後、モデルへ戻る（＝ループ）
    return builder.compile()


# langgraph dev / LangSmith Studio が読み込むグラフ（langgraph.json から参照）。
# ※ Studio 上での実行・状態確認・巻き戻しに使う永続化（チェックポイント）は
#    開発サーバ側が面倒を見るため、ここでは checkpointer を付けずにコンパイルする。
graph = build_studio_graph()


def main():
    print("LangSmith Studio に映すグラフ（7-5 の ReAct ループ）の構造プレビュー:\n")
    # Studio が描くのと同じノード・エッジ構成を Mermaid 記法で書き出す（追加依存なし）。
    print(graph.get_graph().draw_mermaid())
    print(
        "Studio で図として見るには（README 7-7 節）:\n"
        '  pip install -U "langgraph-cli[inmem]"\n'
        "  langgraph dev\n"
        "  → 表示された URL をブラウザで開く"
    )


if __name__ == "__main__":
    main()
