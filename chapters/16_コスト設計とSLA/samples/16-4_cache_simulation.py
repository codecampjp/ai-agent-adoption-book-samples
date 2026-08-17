"""16-4 プロンプトキャッシュのヒット率シミュレーション（オフライン）

変わらない「前置き」(prefix) を再利用するとき、ヒット率が上がるほど実効コストが
どう下がるかを見る。未ヒットは書き込み、ヒットは読み出しとして単純化した試算。
本番では利用モデルのキャッシュ方式と usage に置き換える（本文 16-4）。
"""

from __future__ import annotations

from _common import simulate_cache


def main():
    prefix_tokens = 4_000     # システム＋ツール定義＋固定文脈（毎回同じ前置き）
    requests = 10_000         # このプロンプトを使うリクエスト数
    model = "gpt-5.6-luna"

    print(f"=== プロンプトキャッシュ：前置き{prefix_tokens:,}トークン × "
          f"{requests:,}リクエスト（単純化した試算）===")
    print("  ヒット率 |  キャッシュ無し |  キャッシュ有り |     削減額 | 削減率")
    print("  " + "-" * 62)
    for hit_rate in (0.0, 0.3, 0.5, 0.7, 0.9, 0.95):
        r = simulate_cache(prefix_tokens, requests, hit_rate, model=model)
        print(f"    {hit_rate:>4.0%} | {r['no_cache_cost']:>13.4f} | "
              f"{r['with_cache_cost']:>13.4f} | {r['saving']:>9.4f} | "
              f"{r['saving_ratio']:>5.0%}")

    print()
    print("※ ヒット率0%では書き込み(割高)だけ払い、キャッシュ無しより高くなり得る。")
    print("※ 固定部を前・可変部を後ろに置き、アクセス間隔をTTLに合わせるとヒット率が上がる（本文 16-4）。")


if __name__ == "__main__":
    main()
