"""10-4 複数のMCPサーバーを束ねる ── 完全版（オフライン）

本文 10-4 の骨格を動かす。langchain-mcp-adapters の MultiServerMCPClient で、
2つのローカルMCPサーバー（mcp_servers/ 配下のダミー Confluence／GitHub）を
stdio で束ね、get_tools() で全サーバーのツールをまとめて取り出す。

APIキー・ネットワーク不要（各サーバーは同じ Python でサブプロセス起動）。
本番では、ここに実在のSaaS製リモートサーバー（HTTP）や、第8章で自作した
社内サーバー（stdio）を混在させる。ツール名の衝突は tool_name_prefix で回避。
"""

from __future__ import annotations

import asyncio
import os
import sys

from langchain_mcp_adapters.client import MultiServerMCPClient

HERE = os.path.dirname(os.path.abspath(__file__))


def _server(path: str) -> dict:
    # サブサーバーは本スクリプトと同じ Python で stdio 起動する
    return {"transport": "stdio", "command": sys.executable,
            "args": [os.path.join(HERE, "mcp_servers", path)]}


async def main() -> None:
    client = MultiServerMCPClient(
        {
            "confluence": _server("confluence_server.py"),
            "github": _server("github_server.py"),
            # 本番では自作の社内サーバー（第8章）もここに混ぜられる:
            # "internal": {"transport": "stdio", "command": "python", "args": ["…/server.py"]},
        },
        tool_name_prefix=True,   # 同名ツールの衝突を避ける（confluence_search / github_search）
    )

    # 全サーバーのツールを、まとめて LangChain ツールとして取得
    tools = await client.get_tools()
    print("[取得したツール]", [t.name for t in tools])

    # 各ソースを横断して検索してみる（ツール名は「サーバー名+ツール名」）
    by_name = {t.name: t for t in tools}
    for name in by_name:
        if name.endswith("search"):
            result = await by_name[name].ainvoke({"query": "障害対応 デプロイ"})
            print(f"[{name}] ->", result)


if __name__ == "__main__":
    asyncio.run(main())
