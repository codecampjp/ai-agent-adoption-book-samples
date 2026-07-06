"""8-3 tools / resources / prompts の3分類 ── 完全版

本文 8-3 では、ツール・リソース・プロンプトを別々の小さなコード片で書き分けた。
このファイルはその3つを1つのサーバーにまとめ、そのまま動かせるようにしたもの。

ドライラン（APIキー・ネットワーク不要）として、FastMCP のインメモリ Client で
- tools/list・tools/call（ツールの発見と実行）
- resources/list・resources/read（リソースとテンプレートの読み取り）
- prompts/list（プロンプトの一覧）
を確かめる。

実行:
    python 8-3_primitives.py            # ドライラン
    python 8-3_primitives.py --serve    # stdio サーバーとして起動
"""

from __future__ import annotations

import sys

from fastmcp import FastMCP

mcp = FastMCP("primitives-demo")


# --- ダミーの社内システム（本文では外部システムに見立てている） ----------------
_TICKETS: dict[str, dict] = {}
_CUSTOMERS = {"12345": {"name": "山田太郎", "plan": "standard"}}


# --- ツール：AIが「実行する」もの ----------------------------------------------
@mcp.tool
def create_ticket(title: str, priority: str) -> dict:
    """問い合わせチケットを新規作成し、発番されたIDを返す"""
    ticket_id = f"TICKET-{len(_TICKETS) + 1:04d}"
    _TICKETS[ticket_id] = {"title": title, "priority": priority}
    return {"id": ticket_id, "title": title, "priority": priority}


# --- リソース：AIが「読む」データ（読み取り専用、URI必須） ----------------------
@mcp.resource("config://app")
def get_config() -> dict:
    """アプリの現在の設定を返す（読み取り専用）"""
    return {"version": "1.0", "region": "tokyo"}


# --- リソーステンプレート：URIに {param} を入れるとパラメータで中身が変わる ------
@mcp.resource("customer://{customer_id}")
def get_customer(customer_id: str) -> dict:
    """顧客IDを受け取り、その顧客の基本情報を返す"""
    return _CUSTOMERS.get(customer_id, {"error": "not found"})


# --- プロンプト：やり取りを「定型化する」テンプレート ---------------------------
@mcp.prompt
def summarize_complaint(text: str) -> str:
    """クレーム文を受け取り、要約と推奨対応を尋ねる定型指示を組み立てる"""
    return f"次のクレームを3行で要約し、推奨する一次対応を挙げてください。\n\n{text}"


async def _dry_run() -> None:
    from fastmcp import Client

    async with Client(mcp) as client:
        tools = await client.list_tools()
        print("[tools/list]", [t.name for t in tools])
        created = await client.call_tool(
            "create_ticket", {"title": "ログインできない", "priority": "high"}
        )
        print("[tools/call] create_ticket ->", created.data)

        resources = await client.list_resources()
        print("[resources/list]", [str(r.uri) for r in resources])
        templates = await client.list_resource_templates()
        print("[resource templates]", [t.uriTemplate for t in templates])
        cfg = await client.read_resource("config://app")
        print("[resources/read] config://app ->", cfg[0].text)
        cust = await client.read_resource("customer://12345")
        print("[resources/read] customer://12345 ->", cust[0].text)

        prompts = await client.list_prompts()
        print("[prompts/list]", [p.name for p in prompts])


def main() -> None:
    if "--serve" in sys.argv:
        mcp.run()
        return
    print("[メモ] ドライラン：インメモリ Client で3分類を確認します。\n")
    import asyncio

    asyncio.run(_dry_run())


if __name__ == "__main__":
    main()
