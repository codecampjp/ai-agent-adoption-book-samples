"""ダミー Confluence MCP サーバー（stdio）── 10-4 の横断検索用

本物の Confluence／Atlassian Rovo MCP サーバー（本文 10-4・脚注参照）の代わりに、
オフラインで動く最小のダミーを FastMCP（第8章）で建てる。search ツールを1つ公開する。
"""

from fastmcp import FastMCP

mcp = FastMCP("confluence")

_DOCS = [
    {"id": "doc-CONF-1234", "source": "confluence",
     "excerpt": "先月の障害対応の記録。一次切り分けの後、担当リーダーにエスカレーション。"},
    {"id": "doc-CONF-2000", "source": "confluence",
     "excerpt": "経営会議メモ（役員限り）。未公表の事業再編の検討状況。"},
]


@mcp.tool
def search(query: str) -> list[dict]:
    """Confluence（社内wiki）を検索し、関係する文書の抜粋を返す"""
    return [d for d in _DOCS if any(t in d["excerpt"] for t in query) ] or _DOCS


if __name__ == "__main__":
    mcp.run()
