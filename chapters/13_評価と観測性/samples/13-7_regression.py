"""13-7 回帰テスト風の判定 ── 合格ラインを割ったら失敗として返す（オフライン）

本文 13-7 の「評価データセットの全件を流し、合格ラインを割ったらビルドを止める」を、
擬似エージェント＋擬似ジャッジでオフライン再現する。合格ライン（しきい値）を下回ると、
プロセスを異常終了（exit code 1）する ── CIが赤信号を出して止めるのと同じ骨組み。

本番では、この判定を promptfoo eval や deepeval test run を CI で走らせる形に置き換える。
"""

from __future__ import annotations

import sys

from _common import DATASET, pseudo_agent, judge_output

# 合格ライン：全ケースの平均スコアがこの値以上なら合格（本文 13-7 の「合格ライン」）
PASS_LINE = 0.9


def run_eval() -> float:
    scores = []
    for case in DATASET:
        output = pseudo_agent(case["input"], case["role"])
        result = judge_output(case, output)
        scores.append(result["score"])
        mark = "PASS" if result["score"] >= 1.0 else "WARN"
        print(f"  [{result['id']}] score={result['score']:.2f} {mark}")
    return sum(scores) / len(scores)


def main():
    print("=== 回帰テスト（評価データセット全件）===")
    overall = run_eval()
    print(f"\n全体スコア: {overall:.2f}（合格ライン: {PASS_LINE}）")

    if overall < PASS_LINE:
        # 合格ラインを割った → 失敗として返す（CIならここでビルドが止まる）
        print("赤信号：合格ラインを割りました。変更をマージできません。")
        sys.exit(1)
    print("青信号：合格ラインを満たしています。")


if __name__ == "__main__":
    main()
