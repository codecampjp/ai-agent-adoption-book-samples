"""6-5 ログと観測性を入れた手書きエージェント（停止条件つき）。

本書 6-5（ログと観測性を自前で入れる）の掲載コードを、そのまま実行できる形に
まとめたもの。6-3 の最小ループに対して、次の2つが足されている。

  - 6-4 の停止条件: while True を for step in range(MAX_STEPS) に置き換え、上限で必ず止める。
         for ... else で「break せずに回り切った＝上限到達」を検知して警告する。
         （停止条件だけの版は 6-4_agent_loop_observable.py）
  - 6-5 のログ: 各ステップに print ログを仕込み、stop_reason・トークン・道具呼び出しを記録する。

ツール（get_stock）とモデル名は 6-3 のスクリプトから読み込んで再利用する
（本文と同じく、止め方とログだけを差分として足している様子を示すため）。

このサンプルは2モードで動く。

1. 既定（APIキー不要）:
   実際の API は呼ばず、各ステップのログ出力（[step N] ...）と上限到達の扱いを
   シミュレートして表示する。本文 6-5 の「期待される記録」と同じ形を再現する。

2. 本番（任意）:
   環境変数 ANTHROPIC_API_KEY が設定され、anthropic パッケージが入っていれば、
   実際に Claude へ問い合わせ、上限つきループをログを出しながら回す。

実行:
    python 6-5_agent_loop_observable.py
    ANTHROPIC_API_KEY=sk-... python 6-5_agent_loop_observable.py   # 本番

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
    """ANTHROPIC_API_KEY があれば、上限つきループをログを出しながら回す。"""
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

        # 【ログ】このステップの結果を記録する（stop_reason とトークン）
        print(
            f"[step {step}] stop_reason={response.stop_reason} "
            f"tokens(in/out)={response.usage.input_tokens}/{response.usage.output_tokens}"
        )

        if response.stop_reason != "tool_use":
            break  # 最終回答が返った：正常終了

        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            result = run_tool(block.name, block.input)
            # 【ログ】どの道具を・どんな引数で呼び、何が返ったか
            print(f"[step {step}] tool={block.name} input={block.input} -> {result}")
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
    """APIキーなしのドライラン。本文 6-5 と同じ形のステップログを再現する。"""
    print("[メモ] ANTHROPIC_API_KEY 未設定のため、API は呼ばずにログの形だけを再現します。")
    print(f"依頼: {task}\n")

    # 実際にはモデルが決める部分を、固定の筋書き（A-100品切れ→B-200確認→最終回答）で再現
    trajectory = [
        {"stop": "tool_use", "tok": (512, 45), "code": "A-100"},
        {"stop": "tool_use", "tok": (580, 48), "code": "B-200"},
        {"stop": "end_turn", "tok": (640, 60), "code": None},
    ]
    for step, s in enumerate(trajectory):
        print(f"[step {step}] stop_reason={s['stop']} tokens(in/out)={s['tok'][0]}/{s['tok'][1]}")
        if s["code"] is not None:
            result = run_tool("get_stock", {"product_code": s["code"]})
            print(f"[step {step}] tool=get_stock input={{'product_code': '{s['code']}'}} -> {result}")

    print("\n[メモ] step 2 で stop_reason が tool_use 以外になりループ終了（正常終了）。")
    print("       MAX_STEPS まで回り切ると for...else が発火し『打ち切り』警告になる。")
    print("       実際にモデルに判断・回答させるには ANTHROPIC_API_KEY を設定して再実行。")


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
