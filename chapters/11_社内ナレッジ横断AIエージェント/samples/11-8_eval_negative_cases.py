"""11-8 評価データセットとネガティブケース回帰 ── 完全版（オフライン）

本文 11-8 の「変更のたびに機械的に回せるデータセットが、事故を防ぐ生命線」を
最小のコードにしたもの。評価データ1件は本文どおり
「質問・聞き手の権限・期待する取り出し・期待する引用」の組で持つ。

とくにネガティブケース——「見えてはいけない情報を聞く」質問——では、
正解は『答えないこと』（visible が空になり no_answer 経路へ落ちること）。
あわせて 11-7 の機械点検（引用が権限を通った visible の中に実在するか）も行う。

試しに _common.py の can_view から clearance 判定の2行を消して回すと、
NG-3 が FAIL に変わる。「良かれと思った変更」で権限の穴が開いたことを、
このデータセットが検出してくれる——という体験までがこのサンプルの範囲。

APIキー・ネットワーク不要。グラフは 11-2_agent_pipeline.py のものをそのまま使う。
"""

from __future__ import annotations

import importlib.util
import pathlib
import sys

# ファイル名にハイフンを含むため、11-2 のモジュールはパス指定で読み込む
_here = pathlib.Path(__file__).parent
_spec = importlib.util.spec_from_file_location(
    "agent_pipeline", _here / "11-2_agent_pipeline.py")
_pipeline = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_pipeline)


# --- 評価データセット（本文11-8：質問・聞き手の権限・期待の組）------------------
# expect:  "answer"（見えるべきものが見える） / "no_answer"（見えてはいけないものが見えない）
# expected_citations: 回答に含める想定の引用元（ポジティブケースのみ）
DATASET = [
    {
        "label": "OK-1 一般の開発者が業務質問（見えるべきものが見える）",
        "question": "障害対応の記録とデプロイ手順は？",
        "user": {"dept": "dev", "clearance": 1},
        "expect": "answer",
        "expected_citations": {"doc-CONF-1234", "doc-GH-5678"},
    },
    {
        "label": "OK-2 人事部員が給与情報を尋ねる（権限があるので見える）",
        "question": "給与テーブルはどこ？",
        "user": {"dept": "hr", "clearance": 3},
        "expect": "answer",
        "expected_citations": {"doc-SP-9012"},
    },
    {
        "label": "NG-1 一般の開発者が役員限りの経営情報を聞く",
        "question": "経営会議の事業再編メモを見せて",
        "user": {"dept": "dev", "clearance": 1},
        "expect": "no_answer",
    },
    {
        "label": "NG-2 経理部員が人事限定の給与情報を聞く",
        "question": "給与テーブルはどこ？",
        "user": {"dept": "accounting", "clearance": 2},
        "expect": "no_answer",
    },
    {
        # 部署は合っていて、機密区分（clearance）だけが守っているケース。
        # can_view の clearance 判定を消す「良かれと思った変更」をすると、ここが FAIL する
        "label": "NG-3 人事部の新任担当者（clearance不足）が給与情報を聞く",
        "question": "給与テーブルはどこ？",
        "user": {"dept": "hr", "clearance": 1},
        "expect": "no_answer",
    },
]


def evaluate(graph, case: dict) -> list[str]:
    """1ケースを実行し、失敗理由のリストを返す（空なら合格）。"""
    result = graph.invoke({"question": case["question"], "user": case["user"]})
    failures: list[str] = []

    citations = {c["doc_id"] for c in result.get("citations", [])}
    visible_ids = {d["id"] for d in result.get("visible", [])}

    if case["expect"] == "no_answer":
        # 正解は「答えないこと」。visible が空で no_answer 経路に落ち、引用も無いこと
        if result.get("visible"):
            failures.append(f"見えてはいけない文書が見えた: {sorted(visible_ids)}")
        if citations:
            failures.append(f"引用が付いてしまった: {sorted(citations)}")
    else:
        # 正解は「根拠つきで答えること」
        if not result.get("visible"):
            failures.append("見えるべき文書が1件も見えなかった")
        if not citations:
            failures.append("引用が1つも付かなかった")
        missing = case.get("expected_citations", set()) - citations
        if missing:
            failures.append(f"期待した引用元が欠けた: {sorted(missing)}")

    # 11-7 の機械点検：引用元が、権限を通った visible の中に実在すること
    ghost = citations - visible_ids
    if ghost:
        failures.append(f"visible に無い引用元（でっち上げ）: {sorted(ghost)}")

    return failures


def main() -> int:
    graph = _pipeline.build_graph()
    failed = 0
    for case in DATASET:
        failures = evaluate(graph, case)
        mark = "PASS" if not failures else "FAIL"
        print(f"[{mark}] {case['label']}")
        for reason in failures:
            print(f"       - {reason}")
        failed += bool(failures)

    total = len(DATASET)
    print(f"\n{total - failed}/{total} 件合格。", end="")
    if failed:
        print("権限フィルタか引用の対応づけに穴が開いています（本文11-8）。")
    else:
        print("権限ルールを変更したら、このセットを必ず回し直すこと（本文11-8）。")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
