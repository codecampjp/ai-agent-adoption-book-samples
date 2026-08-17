"""自分の知識ベースの規模で再埋め込みコストを試算する（オフライン）

このスクリプトは本書サンプルリポジトリ限定の追加教材で、本文（第17章）には
登場しない。17-6 の試算モデル（_common.py）に自社の想定値（総チャンク数・
1チャンクの平均トークン・埋め込み単価・変更率）を渡し、全再構築と差分更新の
コストを比べる。

既定の単価 0.10（ドル/100万トークン）は構造を見るための擬似値。実際の試算では
使う埋め込みAPIの料金表の値を --price に渡し、変更率は更新日時・ハッシュ・CDCの
実測に置き換えること（本文 17-6）。

使い方:
  python try_reembedding_cost.py --chunks 250000 --tokens-per-chunk 400
  python try_reembedding_cost.py --chunks 100000 --price 0.02 --change-rates 0.005 0.02 0.10
"""

from __future__ import annotations

import argparse

from _common import Corpus, compare, full_rebuild_cost


def main():
    parser = argparse.ArgumentParser(
        description="全再構築 vs 差分更新のコスト比較（リポジトリ限定の追加教材）"
    )
    parser.add_argument("--chunks", type=int, default=100_000,
                        help="総チャンク数（既定 100000）")
    parser.add_argument("--tokens-per-chunk", type=int, default=512,
                        help="1チャンクの平均トークン数（既定 512）")
    parser.add_argument("--price", type=float, default=0.10,
                        help="埋め込み単価（ドル/100万トークン。既定 0.10 は擬似値）")
    parser.add_argument("--change-rates", type=float, nargs="+",
                        default=[0.001, 0.01, 0.05, 0.20, 1.00],
                        help="比較する変更率（0.0〜1.0 を空白区切りで並べる）")
    args = parser.parse_args()

    corpus = Corpus(num_chunks=args.chunks, tokens_per_chunk=args.tokens_per_chunk,
                    price_per_mtok=args.price)

    print(f"=== 総チャンク {corpus.num_chunks:,} / 1チャンク {corpus.tokens_per_chunk} tok"
          f" / 単価 ${args.price}/100万tok ===")
    print(f"  全再構築コスト（毎回まるごと）: {full_rebuild_cost(corpus):.4f}")
    print()
    print("  変更率 | 変更チャンク |   全再構築 |   差分更新 |   差分/全再構築")
    print("  " + "-" * 60)
    for rate in args.change_rates:
        r = compare(corpus, rate)
        print(f"  {rate*100:5.1f}% | {r['changed_chunks']:>10,} | "
              f"{r['full_rebuild_cost']:>9.4f} | {r['incremental_cost']:>9.4f} | "
              f"{r['ratio_incr_over_full']*100:>6.2f}%")
    print()
    print("※ 単価は使う埋め込みAPIの料金表で、変更率は更新日時・ハッシュ・CDCの実測で置き換える（本文 17-6）。")


if __name__ == "__main__":
    main()
