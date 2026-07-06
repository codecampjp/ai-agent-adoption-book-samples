"""15-8 ROI 試算（オフライン）

削減工数×人件費（リターン）と、初期構築＋運用〔従量＋人手〕コストの天秤を取り、
月間の純益と回収期間を出す。金額は擬似値。式より「入力値を現実的に置けるか」が本質で、
とくに人手の運用コストを数え忘れない（本文 15-8）。
"""

from __future__ import annotations

from _common import ROIInput, estimate_roi


def main():
    cases = {
        "見合うケース": ROIInput(
            reduced_hours_per_month=400,   # 月400時間ぶんの作業を肩代わり
            hourly_wage=3_000,             # 擬似の人件費
            monthly_token_cost=250_000,    # 15-2 の月間試算（従量＋判定＋保管）
            monthly_human_cost=150_000,    # 監視・評価更新・乗り換えの人手
            initial_cost=3_000_000,        # 初期構築
        ),
        "人手を数え忘れると見誤るケース": ROIInput(
            reduced_hours_per_month=120,
            hourly_wage=3_000,
            monthly_token_cost=200_000,
            monthly_human_cost=300_000,    # 実は人手が重い＝見合わない
            initial_cost=3_000_000,
        ),
    }

    for name, x in cases.items():
        r = estimate_roi(x)
        print(f"=== {name}（擬似）===")
        print(f"  月間の見返り（削減額） : {r['monthly_saving']:>12,.0f}")
        print(f"  月間の運用コスト       : {r['monthly_ops_cost']:>12,.0f}")
        print(f"  月間の純益             : {r['net_monthly']:>12,.0f}")
        if r["worth_it"]:
            print(f"  → 投資に見合う。初期構築の回収 : 約 {r['payback_months']} か月")
        else:
            print("  → 月間の純益がマイナス。この入力値では見合わない。")
        print()

    print("※ 削減工数を甘く/運用の人手を過小に置くと、見合わない投資が見合って見える（本文 15-8）。")


if __name__ == "__main__":
    main()
