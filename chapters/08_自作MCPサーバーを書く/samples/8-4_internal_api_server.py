"""8-4 社内APIに接続するMCPサーバー ── 完全版

本文 8-4 では、社内の在庫APIを `httpx`（非同期）で叩いて在庫数を返すツールを、
MCPサーバーとして公開する骨格を載せた。このファイルはその骨格を動かせるようにしたもの。

実運用では、接続先（INVENTORY_API_BASE）とAPIキー（INVENTORY_API_KEY）を
環境変数から読み、本物の社内APIを叩く（本文どおり）。
本サンプルは、APIキー・ネットワーク不要の「ドライラン」も用意した：
環境変数が未設定なら、社内APIの代わりに同梱のダミー在庫を返す。
これで、サーバーの組み立てとツールの往復を、外部接続なしで確かめられる。

実行:
    python 8-4_internal_api_server.py            # ドライラン（ダミー在庫）
    INVENTORY_API_BASE=https://api.example.internal \\
    INVENTORY_API_KEY=xxx python 8-4_internal_api_server.py   # 本物の社内APIを叩く
    python 8-4_internal_api_server.py --serve    # stdio サーバーとして起動
"""

from __future__ import annotations

import os
import sys

import httpx
from fastmcp import FastMCP

mcp = FastMCP("inventory-server")

# 接続先や資格情報は、コードに直書きせず環境変数から読む
API_BASE = os.environ.get("INVENTORY_API_BASE")
API_KEY = os.environ.get("INVENTORY_API_KEY")

# 環境変数が未設定ならドライラン（社内APIの代わりにダミー在庫を返す）
DRY_RUN = not (API_BASE and API_KEY)
_FAKE_STOCK = {"A-100": 0, "B-200": 15}


@mcp.tool
async def get_stock(product_code: str) -> dict:
    """商品コードを受け取り、社内在庫システムから現在の在庫数を返す"""
    if DRY_RUN:
        # ドライラン：社内APIを叩く代わりにダミー在庫を返す
        return {"product_code": product_code, "stock": _FAKE_STOCK.get(product_code, 0)}

    # ここからが本番（本文掲載の骨格そのもの）
    headers = {"Authorization": f"Bearer {API_KEY}"}
    async with httpx.AsyncClient() as client:
        res = await client.get(
            f"{API_BASE}/stock/{product_code}", headers=headers, timeout=10.0
        )
        res.raise_for_status()
        data = res.json()
    return {"product_code": product_code, "stock": data["quantity"]}


async def _dry_run() -> None:
    from fastmcp import Client

    async with Client(mcp) as client:
        tools = await client.list_tools()
        print("[tools/list]", [t.name for t in tools])
        for code in ("A-100", "B-200"):
            result = await client.call_tool("get_stock", {"product_code": code})
            print(f"[tools/call] get_stock({code}) ->", result.data)


def main() -> None:
    if "--serve" in sys.argv:
        mcp.run()
        return
    mode = "ドライラン（ダミー在庫）" if DRY_RUN else f"本番（{API_BASE} を叩く）"
    print(f"[メモ] {mode}。インメモリ Client で在庫照会を確認します。\n")
    import asyncio

    asyncio.run(_dry_run())


if __name__ == "__main__":
    main()
