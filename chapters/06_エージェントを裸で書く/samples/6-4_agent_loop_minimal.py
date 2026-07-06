"""6-4 手書き実装：whileループでtool_useをさばく（最小エージェント）。

本書 6-4 節の掲載コードを、そのまま実行できる形にまとめたもの。
第4章の「一往復のツール使用」を while ループで包み、モデルが
「もう道具は要らない」と判断する（tool_use を返さなくなる）まで
自走させる、最小のエージェントループ。

ループの節目 (a)〜(d) は、本文 6-4 のコードコメントおよび図6-4-1 のラベルと対応する。
  (a) モデルへ問い合わせる（tools を渡す）
  (b) stop_reason は tool_use か？ ── 違えば最終回答なので抜ける
  (c) tool_use を実行し、tool_result を会話に積む ──（a）へ戻る
  (d) 最終回答でループを抜ける

このサンプルは2モードで動く。

1. 既定（APIキー不要）:
   実際の API は呼ばず、「品切れなら代替品を調べる」タスクで
   ループがどう回るか（A-100→品切れ→B-200→在庫あり→最終回答）を
   シミュレートして表示する。

2. 本番（任意）:
   環境変数 ANTHROPIC_API_KEY が設定され、anthropic パッケージが入っていれば、
   実際に Claude へ問い合わせ、while ループでツール使用を自走させる。
   （anthropic の導入: pip install anthropic）

実行:
    python 6-4_agent_loop_minimal.py
    ANTHROPIC_API_KEY=sk-... python 6-4_agent_loop_minimal.py   # 本番

注意:
    モデル名（MODEL）は新しい世代が出るたびに更新される。実行時は
    Anthropic 公式ドキュメントで現行のモデル名を確認して置き換えること。
    確かめたいのはモデルの賢さではなく、「ツール使用をループで回す」骨格であり、
    この骨格はモデルが新しくなっても変わらない。
"""

import os

# 実行時は公式ドキュメントで最新のモデル名を確認して置き換える
MODEL = "claude-sonnet-4-6"

# 既定の依頼：1ステップでは終わらない（品切れなら代替品も調べる）タスク
TASK = (
    "商品A-100の在庫を確認して。品切れなら代替品B-200の在庫も調べて、"
    "両方まとめて報告して。"
)

# --- ツールの「定義」：モデルに渡す仕様の宣言（実装ではない） ---
TOOLS = [
    {
        "name": "get_stock",
        "description": (
            "指定した商品の現在の在庫数を返す。商品コード（例：A-100）を渡すと、"
            "その商品の在庫数を整数で返す。在庫照会に使う。"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "product_code": {
                    "type": "string",
                    "description": "在庫を調べたい商品の商品コード（例：A-100）",
                }
            },
            "required": ["product_code"],
        },
    }
]


# --- ツールの「実装」：実際にアプリ側で動く処理。モデルはこの中身を知らない ---
def get_stock(product_code: str) -> str:
    """在庫DBへの問い合わせを模したダミー実装。A-100は品切れ、B-200は在庫あり。"""
    dummy_stock = {"A-100": 0, "B-200": 15}
    return str(dummy_stock.get(product_code, 0))


# tool 名 → 実装のディスパッチ表（ツールが増えたらここに足す）
TOOL_IMPLEMENTATIONS = {
    "get_stock": get_stock,
}


def run_tool(name: str, tool_input: dict) -> str:
    """tool_use の name / input から、対応する実装を呼び出す。"""
    impl = TOOL_IMPLEMENTATIONS.get(name)
    if impl is None:
        raise ValueError(f"未知のツール: {name}")
    return impl(**tool_input)


def run_with_api(task: str) -> None:
    """ANTHROPIC_API_KEY があれば、実際にエージェントループを回す。"""
    import anthropic

    client = anthropic.Anthropic()  # APIキーは環境変数 ANTHROPIC_API_KEY から
    messages = [{"role": "user", "content": task}]

    while True:
        # (a) モデルへ問い合わせる（tools を渡す）
        response = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            tools=TOOLS,
            messages=messages,
        )
        messages.append({"role": "assistant", "content": response.content})

        # (b) stop_reason は tool_use か？ 道具を要求していない（最終回答）なら抜ける
        if response.stop_reason != "tool_use":
            break

        # (c) tool_use を実行し、tool_result を返す
        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            print(f"[tool_use] {block.name}({block.input})")
            try:
                result = run_tool(block.name, block.input)
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,  # 要求と結果を id で対応づける
                        "content": result,
                    }
                )
            except Exception as exc:  # 失敗は is_error でモデルに伝える
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": str(exc),
                        "is_error": True,
                    }
                )
        messages.append({"role": "user", "content": tool_results})

    # (d) 最終回答でループを抜けた：最後の応答が最終回答
    print("=== 最終回答 ===")
    for block in response.content:
        if block.type == "text":
            print(block.text)


def run_dry(task: str) -> None:
    """APIキーなしのドライラン。ループがどう回るかをシミュレートして示す。"""
    print("[メモ] ANTHROPIC_API_KEY 未設定のため、API は呼ばずに流れだけを表示します。")
    print(f"依頼: {task}\n")

    # 実際にはモデルが観察を見て決める部分を、ここでは固定の筋書きで再現する
    simulated_calls = ["A-100", "B-200"]
    for i, code in enumerate(simulated_calls, start=1):
        print(f"(a) {i}回目の問い合わせ → モデルは get_stock を要求（stop_reason='tool_use'）")
        print(f"(c) アプリがツールを実行：get_stock(product_code={code!r}) -> {run_tool('get_stock', {'product_code': code})!r}")
        if code == "A-100":
            print("    観察：在庫0（品切れ）→ モデルは『代替品も調べよう』と判断\n")
        else:
            print("    観察：在庫15（あり）→ 必要な情報がそろった\n")

    print("(b) 次の問い合わせでモデルは道具を要求しない（stop_reason は tool_use 以外）")
    print("(d) ループを抜ける → 最終回答（例：『商品A-100は品切れですが、代替品B-200が15個あります』）")
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
