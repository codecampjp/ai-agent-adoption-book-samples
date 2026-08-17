"""自作 GitHub 検索 MCP サーバーの最小ダミー（stdio）── 11-5 の横断検索用

GitHub から取り込んだ文書を、権限メタデータ付きの自前インデックスから検索して
返す自作MCPサーバー（本文 11-5 の主線）を、オフラインで動く最小のダミーとして
FastMCP（第8章）で建てる。search ツールを1つ公開する。
"""

from fastmcp import FastMCP

mcp = FastMCP("github")

_DOCS = [
    {"id": "doc-GH-5678", "source": "github",
     "excerpt": "デプロイ手順。main ブランチへのマージ後に CI が自動でステージングへ配備。",
     "meta": {"required_clearance": 1, "dept_scope": None}},
]


@mcp.tool
def search(query: str) -> list[dict]:
    """GitHub由来の自前インデックスを検索し、権限メタデータ付きでファイル/READMEの抜粋を返す"""
    return _DOCS


if __name__ == "__main__":
    mcp.run()
