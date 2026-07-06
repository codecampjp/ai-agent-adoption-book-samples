"""15-2 トークンコストの試算モデル ── 1リクエストから月間へ（オフライン）

1リクエストのトークン内訳（入力/出力/ツール往復/判定分）を積み上げて概算し、
1依頼あたりの呼び出し回数と月間リクエスト数を掛けて月額を出す。単価は擬似値。
本番では API レスポンスの usage と公式の料金表に置き換える（本文 15-1 / 15-2）。
"""

from __future__ import annotations

from _common import RequestTokens, estimate_request_cost, monthly_cost


def main():
    # 例：社内マニュアルを文脈に積む問い合わせ対応エージェント（擬似のトークン数）
    rt = RequestTokens(
        input_tokens=4_000,        # システム＋ツール定義＋マニュアル文脈＋質問
        output_tokens=600,         # 答え
        tool_roundtrip_tokens=1_500,  # ツールを1〜2回呼んだ追加の入出力
        judge_tokens=800,          # ガードレール/LLM-as-a-Judge の判定分
    )
    calls_per_request = 3          # 利用者の1依頼につきモデルを平均3回叩く（ループ等）
    monthly_requests = 100_000     # 月間の利用件数

    for grade in ("light", "heavy"):
        b = estimate_request_cost(rt, grade=grade)
        m = monthly_cost(b["total_per_request"], calls_per_request, monthly_requests)
        print(f"=== グレード: {grade}（擬似単価）===")
        print(f"  入力         : {b['input']:.6f}")
        print(f"  出力         : {b['output']:.6f}")
        print(f"  ツール往復   : {b['tool_roundtrip']:.6f}")
        print(f"  判定(ガード/ジャッジ): {b['judge']:.6f}")
        print(f"  1呼び出しの小計    : {b['total_per_request']:.6f}")
        print(f"  → 1依頼あたり(×{calls_per_request}回) : "
              f"{b['total_per_request'] * calls_per_request:.6f}")
        print(f"  → 月間(×{monthly_requests:,}件) : {m:,.2f}（擬似）")
        print()

    print("※ 単価は擬似値。実額は変動が速いので使う時点の公式で確認（本文 15-1）。")
    print("※ 出力単価は入力より高く、ツール往復・判定分も積み上がる（本文 15-1/15-2）。")


if __name__ == "__main__":
    main()
