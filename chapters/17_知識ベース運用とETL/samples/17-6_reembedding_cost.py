"""17-6 再埋め込みの戦略とコスト試算 ── 全再構築 vs 差分（オフライン）

「何が変わったか」で戦略を選び（文書更新＝差分／モデル変更＝全再構築）、
全再構築と差分更新のコストを比べる。変更率が低いほど差分が圧倒的に安いことを見る。
単価・チャンク数・変更率は擬似値。本番では実際の埋め込み料金と自社の実データに置き換える。
"""

from __future__ import annotations

from _common import Corpus, choose_strategy, compare, full_rebuild_cost


def main():
    # 例：10万チャンクの社内知識ベース（擬似）
    corpus = Corpus(num_chunks=100_000, tokens_per_chunk=512)

    # 1) 「何が変わったか」で戦略を選ぶ（本文 17-6 の意思決定フロー）
    print("=== 何が変わったか → 戦略 ===")
    cases = [
        ("文書だけ更新", True, False),
        ("埋め込みモデルを変更", False, True),
        ("どちらも変わらず", False, False),
    ]
    for label, doc, model in cases:
        print(f"  {label:16s} → {choose_strategy(doc, model)}")
    print()

    # 2) 全再構築のコスト（モデル変更時にコーパス全体を作り直す）
    print("=== 全再構築 vs 差分更新（擬似単価）===")
    print(f"  総チャンク: {corpus.num_chunks:,} / 1チャンク {corpus.tokens_per_chunk} tok")
    print(f"  全再構築コスト（毎回まるごと）: {full_rebuild_cost(corpus):.4f}（擬似）")
    print()

    # 3) 変更率を変えて、差分がどれだけ効くかを比べる
    print("  変更率 | 変更チャンク |   全再構築 |   差分更新 |   差分/全再構築")
    print("  " + "-" * 60)
    for rate in (0.001, 0.01, 0.05, 0.20, 1.00):
        r = compare(corpus, rate)
        print(f"  {rate*100:5.1f}% | {r['changed_chunks']:>10,} | "
              f"{r['full_rebuild_cost']:>9.4f} | {r['incremental_cost']:>9.4f} | "
              f"{r['ratio_incr_over_full']*100:>6.2f}%")
    print()

    print("※ 単価・チャンク数・変更率は擬似値。本番は実際の埋め込み料金と自社の実データに置き換える（本文 17-6）。")
    print("※ PoCでは全再構築も選択肢。本導入時は差分更新へ切り替える必要性を見直す（本文 17-6）。")
    print("※ 差分を効かせるには『何が変わったか』を知る仕組み（更新日時・ハッシュ・CDC＝17-4）が要る。")


if __name__ == "__main__":
    main()
