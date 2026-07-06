"""第10章サンプル共通モジュール ── ダミー社内コーパスと検索・権限の部品

APIキー・ネットワーク不要で章のコードを確かめられるよう、社内文書を模した
小さなコーパスと、ハイブリッド検索（擬似ベクトル＋キーワード）・RRF・リランキング・
権限判定を、外部依存なしの純Pythonで用意する。

本文（10-5/10-6/10-7）の骨格に対応する「動く実体」。実運用では、検索は各データ
ソースのMCPサーバー（10-4）に、権限判定は自社の認可基盤に置き換わる。
"""

from __future__ import annotations

import math
import re
from collections import Counter

# --- ダミー社内コーパス -------------------------------------------------------
# 各文書に権限メタデータ（required_clearance＝必要な機密レベル／dept_scope＝閲覧できる
# 部署。None なら全社公開）を持たせる。date は鮮度（新しい版の優先に使える）。
CORPUS = [
    {
        "id": "doc-CONF-1234", "source": "confluence",
        "text": "先月の障害対応の記録。一次切り分けの後、担当リーダーにエスカレーションする手順を定める。",
        "meta": {"required_clearance": 1, "dept_scope": None}, "date": "2026-06-10",
    },
    {
        "id": "doc-GH-5678", "source": "github",
        "text": "デプロイ手順。main ブランチへのマージ後に CI が自動でステージングへ配備する。",
        "meta": {"required_clearance": 1, "dept_scope": None}, "date": "2026-06-20",
    },
    {
        "id": "doc-SP-3000", "source": "sharepoint",
        "text": "製品Xの最新仕様。対応OSと必要メモリ、既知の制限事項を記載した最新版。",
        "meta": {"required_clearance": 1, "dept_scope": None}, "date": "2026-06-25",
    },
    {
        "id": "doc-SP-2999", "source": "sharepoint",
        "text": "製品Xの仕様（旧版）。対応OSと必要メモリを記載した過去バージョン。",
        "meta": {"required_clearance": 1, "dept_scope": None}, "date": "2025-11-01",
    },
    {
        "id": "doc-SP-9012", "source": "sharepoint",
        "text": "社員の給与テーブルと評価ランクの対応表。人事部の限定資料。",
        "meta": {"required_clearance": 3, "dept_scope": ["hr"]}, "date": "2026-05-01",
    },
    {
        "id": "doc-CONF-2000", "source": "confluence",
        "text": "経営会議メモ。未公表の事業再編の検討状況。役員限り。",
        "meta": {"required_clearance": 5, "dept_scope": ["exec"]}, "date": "2026-06-28",
    },
]

# 抜粋（引用に添える。ここでは本文の先頭を流用）
for _d in CORPUS:
    _d["excerpt"] = _d["text"][:40]


def _tokens(text: str) -> list[str]:
    # ごく素朴な分かち書き（日本語は2-gram、英数字は単語）。学習用の簡易版。
    # 句読点・記号はノイズになるので、まず文字種の切れ目で語を刻んでから2-gram化する。
    words = re.findall(r"[A-Za-z0-9]+", text)
    runs = re.findall(r"[\u3040-\u30ff\u4e00-\u9fff]+", text)  # ひらがな・カタカナ・漢字の連なり
    bigrams = ["".join(pair) for run in runs for pair in zip(run, run[1:])]
    return [w.lower() for w in words] + bigrams


def _cosine(a: Counter, b: Counter) -> float:
    common = set(a) & set(b)
    dot = sum(a[t] * b[t] for t in common)
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    return dot / (na * nb) if na and nb else 0.0


def vector_search(question: str, docs=CORPUS, k: int = 5) -> list[dict]:
    """擬似ベクトル検索：bag-of-words のコサイン類似で近い順に返す（意味検索の代役）。"""
    qv = Counter(_tokens(question))
    scored = [(d, _cosine(qv, Counter(_tokens(d["text"])))) for d in docs]
    scored.sort(key=lambda x: x[1], reverse=True)
    return [d for d, s in scored[:k] if s > 0]


def keyword_search(question: str, docs=CORPUS, k: int = 5) -> list[dict]:
    """キーワード検索：質問語の一致件数が多い順（BM25の代役）。"""
    q = set(_tokens(question))
    scored = [(d, len(q & set(_tokens(d["text"])))) for d in docs]
    scored.sort(key=lambda x: x[1], reverse=True)
    return [d for d, s in scored[:k] if s > 0]


def rrf(rankings: list[list[dict]], k: int = 60) -> list[dict]:
    """RRF（逆順位融合）：各検索の順位だけで統合する（スコアのものさし差を吸収）。"""
    score: dict[str, float] = {}
    by_id: dict[str, dict] = {}
    for ranking in rankings:
        for rank, doc in enumerate(ranking):
            score[doc["id"]] = score.get(doc["id"], 0.0) + 1.0 / (k + rank + 1)
            by_id[doc["id"]] = doc
    ordered = sorted(score, key=lambda i: score[i], reverse=True)
    return [by_id[i] for i in ordered]


def hybrid_search(question: str, docs=CORPUS) -> list[dict]:
    """ハイブリッド検索：ベクトル検索とキーワード検索をRRFで統合する（第3章3-5）。"""
    return rrf([vector_search(question, docs), keyword_search(question, docs)])


def rerank(question: str, candidates: list[dict], top: int = 3, min_overlap: int = 2) -> list[dict]:
    """リランキング：質問語との重なりで関連度を精査し、関連するものだけ上位を残す。

    クロスエンコーダの代役。重なりが min_overlap 未満（＝偶然1語かすっただけ）の候補は
    無関係とみなして落とす。ハイブリッド検索が「ついで」に拾ってきた文書がそのまま
    回答根拠に混ざるのを防ぐ。本番では専用のリランカーがこの役割を担う（第3章3-5）。
    """
    q = set(_tokens(question))
    scored = [(d, len(q & set(_tokens(d["text"])))) for d in candidates]
    relevant = sorted((p for p in scored if p[1] >= min_overlap), key=lambda p: p[1], reverse=True)
    return [d for d, _ in relevant[:top]]


def can_view(user: dict, meta: dict) -> bool:
    """この利用者がこの文書を見てよいか（確定的な権限判定・10-6）。"""
    if user["clearance"] < meta["required_clearance"]:
        return False
    if meta.get("dept_scope") and user["dept"] not in meta["dept_scope"]:
        return False
    return True
