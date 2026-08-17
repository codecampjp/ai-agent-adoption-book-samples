"""第17章サンプル共通モジュール ── 再埋め込みコストの試算（擬似）

APIキー・ネットワーク・外部ライブラリ不要で、本章17-6「再埋め込みの戦略とコスト試算」を
手元で回せるよう、次を純Python（標準ライブラリのみ）で用意する。

  ・全再構築コスト … コーパス全体を作り直す（埋め込みモデル変更時＝本文 17-6）
  ・差分更新コスト … 変わったチャンクだけ作り直す（文書更新時＝本文 17-6）
  ・両者の比較   … 変更率を変えると差がどう開くか（損益）

重要：ここで使う埋め込み単価・チャンク数・変更率は、すべて構造を見るための「擬似値」である。
本番では、この擬似の単価を実際の埋め込みAPIの料金表に、擬似のチャンク数・変更率を自社の
知識ベースの実データ（総チャンク数・1日/1回に変わる割合）に置き換える。
実額は変動が速いので、必ず使う時点の公式ドキュメントで確認すること（本文 17-6）。
"""

from __future__ import annotations

from dataclasses import dataclass

# --- 擬似の埋め込み単価（100万トークンあたり・擬似値）-------------------------
# 2026-07-31時点のOpenAI text-embedding-3-small（$0.02）と
# text-embedding-3-large（$0.13）の価格帯を参考に、$0.10と設定。
# 特定モデルの実額ではない。構造（チャンク数×1チャンクのトークン×単価）だけを見る。
EMBED_PRICE_PER_MTOK = 0.10   # 擬似ドル / 100万トークン

PER_MTOK = 1_000_000


@dataclass
class Corpus:
    """知識ベースの規模（擬似）。"""
    num_chunks: int            # 総チャンク数
    tokens_per_chunk: int = 512  # 1チャンクあたりの平均トークン数
    price_per_mtok: float = EMBED_PRICE_PER_MTOK  # 埋め込み単価（擬似）

    def embed_cost(self, chunks: int) -> float:
        """指定チャンク数を埋め込むコスト（チャンク数 × トークン × 単価）。"""
        tokens = chunks * self.tokens_per_chunk
        return tokens / PER_MTOK * self.price_per_mtok


def full_rebuild_cost(corpus: Corpus) -> float:
    """全再構築：コーパス全体を作り直す（本文 17-6。埋め込みモデル変更時）。"""
    return corpus.embed_cost(corpus.num_chunks)


def incremental_cost(corpus: Corpus, change_rate: float) -> float:
    """差分更新：変わったチャンクだけ作り直す（本文 17-6。文書更新時）。

    change_rate … 0.0〜1.0。1回の更新で変わるチャンクの割合。
    """
    if not 0.0 <= change_rate <= 1.0:
        raise ValueError("change_rate は 0.0〜1.0")
    changed = round(corpus.num_chunks * change_rate)
    return corpus.embed_cost(changed)


def compare(corpus: Corpus, change_rate: float) -> dict:
    """全再構築と差分更新のコストを比べる（本文 17-6）。"""
    full = full_rebuild_cost(corpus)
    incr = incremental_cost(corpus, change_rate)
    return {
        "change_rate": change_rate,
        "changed_chunks": round(corpus.num_chunks * change_rate),
        "full_rebuild_cost": full,
        "incremental_cost": incr,
        "saving": full - incr,
        # 差分が全再構築の何分の1か（例 100分の1 → 0.01）
        "ratio_incr_over_full": (incr / full) if full else 0.0,
    }


def choose_strategy(document_changed: bool, model_changed: bool) -> str:
    """「何が変わったか」から再埋め込み戦略を選ぶ（本文 17-6 の意思決定フロー）。

    優先順位：モデル変更があれば全再構築（ベクトルは互換性がなく混ぜられない）、
    そうでなく文書だけ変わったなら差分、どちらでもなければ何もしない（使い回す）。
    """
    if model_changed:
        return "full_rebuild"   # コーパス全体を作り直し、裏で作って切り替え
    if document_changed:
        return "incremental"    # 変わったチャンクだけ
    return "reuse"              # 使い回す（基本）
