"""16-2 トークンコストの試算モデル ── 1リクエストから月間へ（オフライン）

本文16-2と同じ条件で、1リクエスト、1日、月間の費用を計算する。
単価は2026年7月29日時点のスナップショット。利用時は最新の公式料金に置き換える。
"""

from __future__ import annotations

from _common import RequestTokens, estimate_request_cost, monthly_cost


def main():
    per_day = 1_000
    days = 30
    monthly_requests = per_day * days

    cases = {
        "基準：Terra": ("gpt-5.6-terra", RequestTokens(6_000, 1_000)),
        "出力を500へ": ("gpt-5.6-terra", RequestTokens(6_000, 500)),
        "入力4,000をキャッシュ": (
            "gpt-5.6-terra", RequestTokens(2_000, 1_000, cached_input_tokens=4_000)
        ),
        "すべてLuna": ("gpt-5.6-luna", RequestTokens(6_000, 1_000)),
    }

    print("=== 1リクエスト → 1日 → 月間の試算（USD）===")
    for name, (model, tokens) in cases.items():
        result = estimate_request_cost(tokens, model)
        per_request = result["total_per_request"]
        print(
            f"{name:<24} 1件=${per_request:.4f} "
            f"1日=${per_request * per_day:.2f} "
            f"月間=${monthly_cost(per_request, monthly_requests):,.0f}"
        )

    terra = estimate_request_cost(RequestTokens(6_000, 1_000), "gpt-5.6-terra")
    luna = estimate_request_cost(RequestTokens(6_000, 1_000), "gpt-5.6-luna")
    routed = terra["total_per_request"] * 0.2 + luna["total_per_request"] * 0.8
    print(
        f"{'80% Luna / 20% Terra':<24} 1件=${routed:.4f} "
        f"1日=${routed * per_day:.2f} "
        f"月間=${monthly_cost(routed, monthly_requests):,.0f}"
    )
    print()
    print("※ 1件には、利用者の依頼を完了するまでの内部モデル呼び出しをすべて含める。")
    print("※ モデル切り替えや出力削減は、評価の合格ラインを満たすことを確認して採用する。")


if __name__ == "__main__":
    main()
