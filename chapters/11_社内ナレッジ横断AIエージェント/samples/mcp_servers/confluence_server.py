"""自作 Confluence 検索 MCP サーバーの最小ダミー（stdio）── 11-5 の横断検索用

Confluence から取り込んだ文書を、権限メタデータ付きの自前インデックスから検索して
返す自作MCPサーバー（本文 11-5 の主線）を、オフラインで動く最小のダミーとして
FastMCP（第8章）で建てる。search ツールを1つ公開する。
"""

from fastmcp import FastMCP

mcp = FastMCP("confluence")

_DOCS = [
    {"id": "doc-CONF-1234", "source": "confluence",
     "excerpt": "先月の障害対応の記録。一次切り分けの後、担当リーダーにエスカレーション。",
     "meta": {"required_clearance": 1, "dept_scope": None}},
    {"id": "doc-CONF-2000", "source": "confluence",
     "excerpt": "経営会議メモ（役員限り）。未公表の事業再編の検討状況。",
     "meta": {"required_clearance": 5, "dept_scope": ["exec"]}},
]


@mcp.tool
def search(query: str) -> list[dict]:
    """Confluence由来の自前インデックスを検索し、権限メタデータ付きで文書の抜粋を返す"""
    return [d for d in _DOCS if any(t in d["excerpt"] for t in query) ] or _DOCS


if __name__ == "__main__":
    mcp.run()
