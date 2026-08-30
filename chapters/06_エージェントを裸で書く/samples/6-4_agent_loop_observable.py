"""6-4 停止条件を入れた手書きエージェント。

本書 6-4（停止条件をどう設計するか）の掲載コードを、そのまま実行できる形に
まとめたもの。6-3 の最小ループに対して、止め方だけを差分として足している。

  - while True を for step in range(MAX_STEPS) に置き換え、上限で必ず止める。
  - for ... else で「break せずに回り切った＝上限到達」を検知して警告する。

ステップごとのログ（stop_reason・トークン・道具呼び出しの記録）は、
次の 6-5_agent_loop_observable.py で足す。

ツール（get_stock）とモデル名は 6-3 のスクリプトから読み込んで再利用する
（本文と同じく、止め方だけを差分として足している様子を示すため）。

このサンプルは2モードで動く。

1. 既定（APIキー不要）:
   実際の API は呼ばず、上限つきループがどう回り、どう止まるか
   （正常終了と上限到達の2つの止まり方）をシミュレートして表示する。

2. 本番（任意）:
   環境変数 ANTHROPIC_API_KEY が設定され、anthropic パッケージが入っていれば、
   実際に Claude へ問い合わせ、上限つきループを回す。

実行:
    python 6-4_agent_loop_observable.py
    ANTHROPIC_API_KEY=sk-... python 6-4_agent_loop_observable.py   # 本番

注意:
    モデル名は 6-3 の MODEL を共有する。新しい世代が出たら 6-3 側を更新すれば
    こちらにも反映される。実行時は公式ドキュメントで現行のモデル名を確認すること。
"""

import importlib
import os

# 6-3 のスクリプトからツール定義・実装・モデル名を再利用する。
# ファイル名が数字始まりで通常の import が使えないため importlib を使う。
_base = importlib.import_module("6-3_agent_loop_minimal")
MODEL = _base.MODEL
TOOLS = _base.TOOLS
run_tool = _base.run_tool

MAX_STEPS = 10  # 道具の使用回数の上限（暴走への最後の砦）

TASK = "商品A-100の在庫を確認して。品切れなら代替品B-200の在庫も調べて報告して。"


def run_with_api(task: str) -> None:
    """ANTHROPIC_API_KEY があれば、上限つきループを回す。"""
    import anthropic

    client = anthropic.Anthropic()
    messages = [{"role": "user", "content": task}]

    for step in range(MAX_STEPS):
        response = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            tools=TOOLS,
            messages=messages,
        )
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason != "tool_use":
            break  # 最終回答が返った：正常終了

        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            result = run_tool(block.name, block.input)
            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": str(result),
                }
            )
        messages.append({"role": "user", "content": tool_results})
    else:
        # for を break せずに回り切った＝上限到達（異常な打ち切り）
        print("警告：最大反復回数に達したため打ち切りました")
        return

    print("=== 最終回答 ===")
    for block in response.content:
        if block.type == "text":
            print(block.text)


def run_dry(task: str) -> None:
    """APIキーなしのドライラン。上限つきループの2つの止まり方を示す。"""
    print("[メモ] ANTHROPIC_API_KEY 未設定のため、API は呼ばずに流れだけを表示します。")
    print(f"依頼: {task}\n")
    print(f"ループは for step in range(MAX_STEPS)（上限 {MAX_STEPS} 回）で回る。\n")

    # 実際にはモデルが決める部分を、固定の筋書き（A-100品切れ→B-200確認→最終回答）で再現
    simulated_calls = ["A-100", "B-200"]
    for step, code in enumerate(simulated_calls):
        result = run_tool("get_stock", {"product_code": code})
        print(f"step {step}: モデルが get_stock を要求 → get_stock(product_code={code!r}) -> {result!r}")

    print(f"step {len(simulated_calls)}: モデルは道具を要求しない（stop_reason が tool_use 以外）→ break で正常終了")
    print("\n止まり方は2つ:")
    print("  1. 正常終了 …… 最終回答が返り、break でループを抜ける（今回の筋書き）")
    print(f"  2. 上限到達 …… {MAX_STEPS} 回 break せずに回り切ると for...else が発火し、")
    print("     『警告：最大反復回数に達したため打ち切りました』と表示して止まる")
    print("\n[メモ] 実際にモデルに判断・回答させるには ANTHROPIC_API_KEY を設定して再実行。")


def main() -> None:
    if os.environ.get("ANTHROPIC_API_KEY"):
        try:
            run_with_api(TASK)
            return
        except ImportError:
            print("[メモ] anthropic 未導入のためドライランに切り替え（pip install anthropic）\n")
    run_dry(TASK)


if __name__ == "__main__":
    main()
