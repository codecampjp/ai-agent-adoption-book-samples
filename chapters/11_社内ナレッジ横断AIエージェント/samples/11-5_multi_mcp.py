"""11-5 複数のMCPサーバーを束ねる ── 完全版（オフライン）

本文 11-5 の骨格を動かす。langchain-mcp-adapters の MultiServerMCPClient で、
2つの自作MCPサーバーの最小ダミー（mcp_servers/ 配下。各ソースの権限メタデータ付き
自前インデックスを検索する想定）を stdio で束ね、get_tools() でまとめて取り出す。

APIキー・ネットワーク不要（各サーバーは同じPythonで子プロセス起動）。
本番では、各ソースの取り込み済みインデックスを検索する自作サーバー（第8章）を建てる。
独立したMCPサーバーをURLで公開する場合は、同じクライアントへStreamable HTTPで接続できる。
自作か公式かは、トランスポートの選択基準ではない（本文11-5）。
ツール名の衝突は tool_name_prefix で回避。
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
            # クライアントが起動する子プロセスはstdio、
            # URLで到達できる独立サーバーはStreamable HTTP。
            # 自作か公式かは、トランスポートの選択基準ではない。
            # "github_remote": {"transport": "http", "url": "http://localhost:8000/mcp"},
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
