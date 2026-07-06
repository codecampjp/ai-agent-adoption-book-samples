"""13-5 観測性 ── 実行トレース（擬似スパン）を1件ダンプする（オフライン）

本文 13-5 の「トレース＝1リクエストの全行程／スパン＝個々の処理」の形を、擬似スパンで見せる。
1件のリクエストを流し、どのノード（処理）が何を受け取り何を返したかを木のように並べる。

本番では、この擬似スパンのダンプが LangSmith / Langfuse の整ったトレース画面に置き換わる。
"""

from __future__ import annotations

import json

from _common import pseudo_agent


def main():
    query, role = "先月の障害対応の記録はどこ？", "engineer"
    output = pseudo_agent(query, role)

    print("=== 擬似トレース（1リクエストの全行程）===")
    print(f"trace: 入力='{query}' 権限={role}")
    for i, span in enumerate(output["spans"], 1):
        print(f"  span {i}: {span['name']}")
        print(f"      in  = {json.dumps(span['in'], ensure_ascii=False)}")
        print(f"      out = {json.dumps(span['out'], ensure_ascii=False)}")
    print(f"  最終出力: {output['answer']}")
    print("\n※ このスパンの並びが、そのまま Trajectory Eval の評価対象（道筋）になる")


if __name__ == "__main__":
    main()
