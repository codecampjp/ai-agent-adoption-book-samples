"""8-1 MCPサーバーの最小構成 ── 完全版

本文 8-1 では、足し算の道具を1つだけ公開する最小のMCPサーバーの骨格を載せた。
このファイルはその骨格をそのまま動かせるようにしたもの。

通常、stdio サーバーは `mcp.run()` で起動して「ホスト（AIアプリ）からの接続」を待ち受ける。
ただ、それだとホストを用意しないと動きを確認できない。そこで本サンプルは、
APIキー・ネットワーク不要の「ドライラン」として、FastMCP のインメモリ Client で
自分のサーバーにつなぎ、tools/list（道具の一覧）と tools/call（実行）を確かめる。

実行:
    python 8-1_minimal_server.py            # ドライラン（インメモリ Client で確認）
    python 8-1_minimal_server.py --serve    # 本物の stdio サーバーとして起動（ホストから接続）
"""

from __future__ import annotations

import sys

from fastmcp import FastMCP

mcp = FastMCP("demo-server")          # サーバーの実体を1つ作る


@mcp.tool                              # この関数を「ツール」として公開する目印
def add(a: int, b: int) -> int:
    """2つの整数を足して返す"""
    return a + b


async def _dry_run() -> None:
    """インメモリ Client で自分のサーバーにつなぎ、発見と実行を確かめる。"""
    from fastmcp import Client

    async with Client(mcp) as client:
        tools = await client.list_tools()
        print("[tools/list] 公開中の道具:", [t.name for t in tools])
        result = await client.call_tool("add", {"a": 2, "b": 3})
        print("[tools/call] add(2, 3) ->", result.data)


def main() -> None:
    if "--serve" in sys.argv:
        # 本物の stdio サーバーとして起動（Claude Desktop などのホストから接続する）
        mcp.run()
        return
    print("[メモ] ドライラン：インメモリ Client で自分のサーバーを確認します。")
    print("       本物の stdio サーバーとして起動するには --serve を付けてください。\n")
    import asyncio

    asyncio.run(_dry_run())


if __name__ == "__main__":
    main()
