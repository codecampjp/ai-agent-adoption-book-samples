"""14-7 回帰テスト風の判定（オフライン）

本文14-7の2種類の基準を再現する。
  ・個別ケースのしきい値：各ケースのスコアが基準以上か
  ・データセット全体の合格率：個別のしきい値を満たしたケースの割合
重大な異常系は、全体の合格率とは別に、1件でも落ちたら失敗とする。

本番では、この判定を評価基盤やpromptfooからCIへ返す。
"""

from __future__ import annotations

import sys

from _common import DATASET, pseudo_agent, judge_output

# このサンプル用の設定値。実運用では業務リスク、HITL、導入段階に応じて決める。
CASE_THRESHOLD = 0.8
PASS_RATE_LINE = 0.9


def run_eval() -> tuple[float, list[str]]:
    passed_cases = 0
    critical_failures = []

    for case in DATASET:
        output = pseudo_agent(case["input"], case["role"])
        result = judge_output(case, output)
        case_passed = result["score"] >= CASE_THRESHOLD
        if case_passed:
            passed_cases += 1

        is_critical = case["expected"]["must_refuse"]
        mark = "PASS" if case_passed else "FAIL"
        tag = "（重大）" if is_critical else ""
        print(f"  [{result['id']}] score={result['score']:.2f} {mark}{tag}")

        # 重大な異常系は、すべての観点を満たすことを個別に要求する。
        if is_critical and result["score"] < 1.0:
            critical_failures.append(result["id"])

    pass_rate = passed_cases / len(DATASET)
    return pass_rate, critical_failures


def main():
    print("=== 回帰テスト（評価データセット全件）===")
    pass_rate, critical_failures = run_eval()
    print(
        f"\n全体合格率: {pass_rate:.0%}"
        f"（個別しきい値: {CASE_THRESHOLD:.1f}／全体の合格ライン: {PASS_RATE_LINE:.0%}）"
    )

    if critical_failures:
        print(
            "赤信号：重大なケースが落ちました"
            f"（{', '.join(critical_failures)}）。変更をマージできません。"
        )
        sys.exit(1)

    if pass_rate < PASS_RATE_LINE:
        print("赤信号：全体の合格ラインを下回りました。変更をマージできません。")
        sys.exit(1)

    print("青信号：個別ケースと全体の基準を満たしています。")


if __name__ == "__main__":
    main()
