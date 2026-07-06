"""ダミー GitHub MCP サーバー（stdio）── 10-4 の横断検索用

本物の GitHub 公式 MCP サーバー（本文 10-4・脚注参照）の代わりに、オフラインで
動く最小のダミーを FastMCP（第8章）で建てる。search ツールを1つ公開する。
"""

from fastmcp import FastMCP

mcp = FastMCP("github")

_DOCS = [
    {"id": "doc-GH-5678", "source": "github",
     "excerpt": "デプロイ手順。main ブランチへのマージ後に CI が自動でステージングへ配備。"},
]


@mcp.tool
def search(query: str) -> list[dict]:
    """GitHub（社内リポジトリ）を検索し、関係するファイル/READMEの抜粋を返す"""
    return _DOCS


if __name__ == "__main__":
    mcp.run()
