"""10-5 横断ハイブリッド検索 ── 完全版（オフライン）

本文 10-5 の骨格（ベクトル検索＋キーワード検索→RRF統合→リランキング）を、
ダミーコーパス（_common.py）の上で動かす。APIキー・ネットワーク不要。

実運用では、各ソースへの問い合わせは 10-4 の MCP 経由になり、埋め込みは本物の
埋め込みモデル、リランキングは専用リランカーに置き換わる（第3章3-5）。
"""

from __future__ import annotations

from _common import vector_search, keyword_search, hybrid_search, rerank

QUESTION = "先月の障害対応の記録と、その後のデプロイ手順は？"


def main() -> None:
    print(f"[質問] {QUESTION}\n")

    v = vector_search(QUESTION)
    print("[ベクトル検索の順位]", [d["id"] for d in v])

    k = keyword_search(QUESTION)
    print("[キーワード検索の順位]", [d["id"] for d in k])

    fused = hybrid_search(QUESTION)
    print("[RRFで統合した順位]", [d["id"] for d in fused])

    top = rerank(QUESTION, fused, top=3)
    print("[リランキング後の上位3件]", [d["id"] for d in top])
    print("\n上位の中身:")
    for d in top:
        print(f"  - {d['id']}（{d['source']}）: {d['excerpt']}")


if __name__ == "__main__":
    main()
