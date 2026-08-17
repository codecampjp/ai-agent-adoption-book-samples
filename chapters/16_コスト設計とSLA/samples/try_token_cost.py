"""自分の条件でトークンコストを試算する（オフライン）

このスクリプトは本書サンプルリポジトリ限定の追加教材で、本文（第16章）には
登場しない。16-2 の試算モデル（_common.py）に自分のトークン数・件数を渡し、
1リクエスト → 1日 → 月間のコストを計算する。

単価は _common.PRICING のスナップショット（2026年7月29日時点）を使う。
実際の料金・モデル名は変わるため、使う時点の公式料金で確認すること。

使い方:
  python try_token_cost.py --input 6000 --output 1000
  python try_token_cost.py --model gpt-5.6-terra --input 2000 --cached 4000 \
                           --output 1000 --per-day 500 --days 20
"""

from __future__ import annotations

import argparse

from _common import PRICING, RequestTokens, estimate_request_cost, monthly_cost


def main():
    parser = argparse.ArgumentParser(
        description="1リクエスト→1日→月間のコスト試算（リポジトリ限定の追加教材）"
    )
    parser.add_argument("--model", choices=sorted(PRICING), default="gpt-5.6-terra",
                        help="単価表のモデル名（既定 gpt-5.6-terra）")
    parser.add_argument("--input", type=int, default=6_000,
                        help="1件あたりの通常入力トークン（既定 6000）")
    parser.add_argument("--cached", type=int, default=0,
                        help="1件あたりのキャッシュ済み入力トークン（既定 0）")
    parser.add_argument("--output", type=int, default=1_000,
                        help="1件あたりの出力トークン（既定 1000）")
    parser.add_argument("--per-day", type=int, default=1_000,
                        help="1日のリクエスト件数（既定 1000）")
    parser.add_argument("--days", type=int, default=30,
                        help="月の稼働日数（既定 30）")
    args = parser.parse_args()

    rt = RequestTokens(args.input, args.output, cached_input_tokens=args.cached)
    r = estimate_request_cost(rt, args.model)
    per_request = r["total_per_request"]
    monthly_requests = args.per_day * args.days

    print(f"=== {args.model}: 入力{args.input:,} + キャッシュ済み{args.cached:,} "
          f"→ 出力{args.output:,} tok ===")
    print(f"  内訳: 入力=${r['input']:.4f} キャッシュ済み=${r['cached_input']:.4f} "
          f"出力=${r['output']:.4f}")
    print(f"  1件  = ${per_request:.4f}")
    print(f"  1日  = ${per_request * args.per_day:,.2f}（{args.per_day:,}件）")
    print(f"  月間 = ${monthly_cost(per_request, monthly_requests):,.2f}"
          f"（{monthly_requests:,}件）")
    print()
    print("※ 1件には、利用者の依頼を完了するまでの内部モデル呼び出しをすべて含めて数える。")
    print("※ 単価は2026年7月29日時点のスナップショット。実際は使う時点の公式料金で確認する。")


if __name__ == "__main__":
    main()
