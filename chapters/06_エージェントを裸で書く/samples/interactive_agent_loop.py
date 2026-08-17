"""対話型エージェントループ観察ツール（本サンプルリポジトリ限定の追加教材）。

※ このファイルは書籍本文には登場しない。リポジトリ独自の追加教材である。

6-3（最小エージェントループ）と 6-5（停止条件とログ）を土台に、自分で入力した
質問に対してエージェントループが回る様子を、1ステップずつ観察できるようにしたもの。

各ステップで表示するのは次の4点。本文 6-3 の (a)〜(d) に対応する。

  1. LLM 呼び出し     … (a) モデルへ問い合わせ、stop_reason とトークン数を表示
  2. ツール選択       … (b) モデルが tool_use を返したか（どの道具・どの引数か）
  3. ツール実行       … (c) アプリ側で実装を呼び、結果（tool_result）を会話に積む
  4. 最終回答         … (d) tool_use が返らなくなったらループを抜けて回答を表示

ツール定義・実装・モデル名は 6-3 のスクリプトから読み込んで再利用する。
使える道具は在庫照会 get_stock のみ（ダミー在庫：A-100=0、B-200=15）。
「A-100 の在庫は？品切れなら代替品 B-200 も調べて」のような質問だとループが
複数回回る様子を観察しやすい。在庫と関係ない質問をすると、モデルが道具を
使わずに直接答える（＝1ステップで終わる）様子も確かめられる。

このサンプルは2モードで動く。

1. 本番（ANTHROPIC_API_KEY 設定時）:
   入力した質問を実際に Claude へ送り、ループを自走させながら各ステップを表示する。

2. ドライラン（APIキー未設定時）:
   API は呼ばず、どんな質問を入れても固定の筋書き（A-100 品切れ → B-200 確認 →
   最終回答）でループの回り方だけを再現する。ループの仕組みの観察用。

実行:
    python interactive_agent_loop.py
    python interactive_agent_loop.py --max-steps 5

終了: 空行を入力するか、Ctrl+C（または Ctrl+D）。

注意:
    質問は独立した1回ずつの実行として扱う（前の質問の会話は持ち越さない）。
    モデル名は 6-3 の MODEL を共有する。新しい世代が出たら 6-3 側を更新する。
"""

from __future__ import annotations

import argparse
import importlib
import os

# 6-3 のスクリプトからツール定義・実装・モデル名を再利用する。
# ファイル名が数字始まりで通常の import が使えないため importlib を使う。
_base = importlib.import_module("6-3_agent_loop_minimal")
MODEL = _base.MODEL
TOOLS = _base.TOOLS
run_tool = _base.run_tool


def run_question_with_api(client, question: str, max_steps: int) -> None:
    """入力された質問1件に対して、上限つきエージェントループを回して観察する。"""
    messages = [{"role": "user", "content": question}]
    response = None

    for step in range(max_steps):
        # 1. LLM 呼び出し（本文 6-3 の (a)）
        print(f"[step {step}] 1. LLM 呼び出し（tools を渡して問い合わせ）")
        response = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            tools=TOOLS,
            messages=messages,
        )
        messages.append({"role": "assistant", "content": response.content})
        print(
            f"[step {step}]    stop_reason={response.stop_reason} "
            f"tokens(in/out)={response.usage.input_tokens}/{response.usage.output_tokens}"
        )

        # 2. ツール選択（本文 6-3 の (b)）：tool_use でなければ最終回答
        if response.stop_reason != "tool_use":
            print(f"[step {step}] 2. ツール選択：モデルは道具を要求しなかった → 最終回答へ")
            break

        # 3. ツール実行（本文 6-3 の (c)）：結果を tool_result として会話に積む
        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            print(f"[step {step}] 2. ツール選択：{block.name}({block.input})")
            try:
                result = run_tool(block.name, block.input)
                print(f"[step {step}] 3. ツール実行 -> {result}")
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": str(result),
                    }
                )
            except Exception as exc:  # 失敗は is_error でモデルに伝える
                print(f"[step {step}] 3. ツール実行 -> 失敗: {exc}")
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": str(exc),
                        "is_error": True,
                    }
                )
        messages.append({"role": "user", "content": tool_results})
    else:
        # break せずに回り切った＝上限到達（本文 6-4 の停止条件）
        print(f"警告：最大反復回数（{max_steps}）に達したため打ち切りました")
        return

    # 4. 最終回答（本文 6-3 の (d)）
    print("=== 4. 最終回答 ===")
    for block in response.content:
        if block.type == "text":
            print(block.text)


def run_question_dry(question: str) -> None:
    """APIキーなしのドライラン。入力によらず固定の筋書きでループの形だけを示す。"""
    print("[メモ] ドライランのため、入力によらず固定の筋書きで流れを再現します。")
    print(f"       （入力した質問: {question}）\n")

    trajectory = [
        {"stop": "tool_use", "tok": (512, 45), "code": "A-100"},
        {"stop": "tool_use", "tok": (580, 48), "code": "B-200"},
        {"stop": "end_turn", "tok": (640, 60), "code": None},
    ]
    for step, s in enumerate(trajectory):
        print(f"[step {step}] 1. LLM 呼び出し（tools を渡して問い合わせ）")
        print(
            f"[step {step}]    stop_reason={s['stop']} "
            f"tokens(in/out)={s['tok'][0]}/{s['tok'][1]}"
        )
        if s["code"] is not None:
            result = run_tool("get_stock", {"product_code": s["code"]})
            print(f"[step {step}] 2. ツール選択：get_stock({{'product_code': '{s['code']}'}})")
            print(f"[step {step}] 3. ツール実行 -> {result}")
        else:
            print(f"[step {step}] 2. ツール選択：モデルは道具を要求しなかった → 最終回答へ")
    print("=== 4. 最終回答（例） ===")
    print("商品A-100は品切れですが、代替品B-200が15個あります。")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "自分の質問を入力して、エージェントループの各ステップ"
            "（LLM呼び出し→ツール選択→実行→最終回答）を観察する。"
            "本サンプルリポジトリ限定の追加教材（書籍本文には登場しない）。"
        )
    )
    parser.add_argument(
        "--max-steps",
        type=int,
        default=10,
        help="道具の使用回数の上限（既定: 10。本文 6-4 の停止条件）",
    )
    args = parser.parse_args()

    client = None
    if os.environ.get("ANTHROPIC_API_KEY"):
        try:
            import anthropic

            client = anthropic.Anthropic()
            print(f"[メモ] 本番モード：入力した質問を実際に Claude（{MODEL}）へ送ります。")
        except ImportError:
            print("[メモ] anthropic 未導入のためドライランに切り替え（pip install anthropic）")
    else:
        print("[メモ] ANTHROPIC_API_KEY 未設定のため、API は呼ばずに流れだけを表示します。")

    print("使える道具: get_stock（ダミー在庫 A-100=0, B-200=15）")
    print("終了: 空行を入力するか Ctrl+C\n")

    while True:
        try:
            question = input("質問> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not question:
            break

        print()
        try:
            if client is not None:
                run_question_with_api(client, question, args.max_steps)
            else:
                run_question_dry(question)
        except KeyboardInterrupt:
            print("\n[メモ] この質問の処理を中断しました。")
        print()


if __name__ == "__main__":
    main()
