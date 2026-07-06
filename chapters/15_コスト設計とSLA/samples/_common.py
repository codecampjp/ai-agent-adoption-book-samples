"""第15章サンプル共通モジュール ── コストとSLAの試算（擬似）

APIキー・ネットワーク・外部ライブラリ不要で、本章のコスト設計を手元で回せるよう、
次を純Python（標準ライブラリのみ）で用意する。

  ・トークンコストの試算   … 入力/出力/ツール往復/判定分を積み上げ、月間へ（本文 15-1 / 15-2）
  ・プロンプトキャッシュ    … ヒット率でコストがどう変わるかのシミュレーション（本文 15-4）
  ・レート制限のスロットリング … 上限超過を待って再試行し、全体をならす（本文 15-5）
  ・ROI 試算              … 削減工数と運用コストから見返りと回収期間（本文 15-8）

重要：ここで使う単価・レート上限は、すべて構造を見るための「擬似値」である。
本番では、この擬似の単価表を実際の料金表に、擬似のレート上限を契約ティアの実値に、
擬似のトークン数を API レスポンスの usage（input_tokens / output_tokens /
cache_creation_input_tokens / cache_read_input_tokens）に置き換える。
実額は変動が速いので、必ず使う時点の公式ドキュメントで確認すること（本文 15-1）。
"""

from __future__ import annotations

from dataclasses import dataclass, field

# --- 擬似の単価表（100万トークンあたり・擬似値）--------------------------------
# 構造だけ本物に合わせている：出力 > 入力、キャッシュ書き込み > 入力、
# キャッシュ読み出し << 入力（本文 15-1 / 15-4）。実額ではない。
#   grade … "light"（軽量・安い）/ "heavy"（高性能・高い）(本文 15-3)

PRICING: dict[str, dict[str, float]] = {
    # 単位：擬似ドル / 100万トークン
    "light": {"input": 1.0, "output": 5.0, "cache_write": 1.25, "cache_read": 0.10},
    "heavy": {"input": 5.0, "output": 25.0, "cache_write": 6.25, "cache_read": 0.50},
}

PER_MTOK = 1_000_000


def _cost(tokens: int, price_per_mtok: float) -> float:
    """トークン数 × 100万トークンあたり単価。"""
    return tokens / PER_MTOK * price_per_mtok


# --- 1リクエストのトークン内訳（本文 15-2）------------------------------------
# 入力・出力に加え、ツール往復ぶん・ガードレール/ジャッジの判定ぶんも積み上がる。

@dataclass
class RequestTokens:
    input_tokens: int          # システムプロンプト＋ツール定義＋文脈＋質問
    output_tokens: int         # モデルが返す答え
    tool_roundtrip_tokens: int = 0   # ツール結果を受けた追加の入出力（本文 15-2）
    judge_tokens: int = 0            # ガードレール/LLM-as-a-Judge の判定分（本文 15-1）


def estimate_request_cost(rt: RequestTokens, grade: str = "light") -> dict:
    """1リクエストの概算コストを内訳つきで返す（本文 15-2 の試算式）。"""
    p = PRICING[grade]
    breakdown = {
        "input": _cost(rt.input_tokens, p["input"]),
        "output": _cost(rt.output_tokens, p["output"]),
        # ツール往復・判定分は、ここでは入力単価で粗く積む（実際は入出力が混ざる）
        "tool_roundtrip": _cost(rt.tool_roundtrip_tokens, p["input"]),
        "judge": _cost(rt.judge_tokens, p["input"]),
    }
    breakdown["total_per_request"] = sum(breakdown.values())
    breakdown["grade"] = grade
    return breakdown


def monthly_cost(per_request_cost: float, calls_per_request: int,
                 monthly_requests: int) -> float:
    """月間コスト ≒ 1件のコスト × 1依頼あたりの呼び出し回数 × 月間リクエスト数。

    「利用者から見た1件」と「課金される呼び出し回数」は一致しない（本文 15-2）。
    ループやガードレールで calls_per_request は 1 より大きくなる。
    """
    return per_request_cost * calls_per_request * monthly_requests


# --- プロンプトキャッシュのヒット率シミュレーション（本文 15-4）----------------
# 変わらない「前置き」(prefix) を再利用する。キャッシュ無しでは毎回 input 単価、
# キャッシュ有りでは初回など未ヒット分は書き込み単価、ヒット分は読み出し単価。

def simulate_cache(prefix_tokens: int, requests: int, hit_rate: float,
                   grade: str = "light") -> dict:
    """前置き部分について、キャッシュ無し/有りの入力コストを比べる（本文 15-4）。

    hit_rate … 0.0〜1.0。前置きがキャッシュにヒットする割合。
    """
    if not 0.0 <= hit_rate <= 1.0:
        raise ValueError("hit_rate は 0.0〜1.0")
    p = PRICING[grade]
    hits = round(requests * hit_rate)
    misses = requests - hits

    no_cache = _cost(prefix_tokens, p["input"]) * requests
    with_cache = (
        _cost(prefix_tokens, p["cache_write"]) * misses   # 未ヒット＝書き込み（割高）
        + _cost(prefix_tokens, p["cache_read"]) * hits     # ヒット＝読み出し（安い）
    )
    saving = no_cache - with_cache
    return {
        "hit_rate": hit_rate,
        "hits": hits,
        "misses": misses,
        "no_cache_cost": no_cache,
        "with_cache_cost": with_cache,
        "saving": saving,
        "saving_ratio": (saving / no_cache) if no_cache else 0.0,
    }


# --- レート制限のスロットリング（本文 15-5）-----------------------------------
# RPM（1分あたりのリクエスト上限）を、1秒あたり rpm/60 だけ回復するトークンバケット
# で表す。バーストで来たリクエストは、枠が空くまで「待って再試行」される（＝429 を
# 指数バックオフで受け流す挙動の擬似）。乱数を使わず決定的に動かす。

def simulate_throttling(num_requests: int, rpm_limit: int) -> dict:
    """num_requests 件がほぼ同時に来たときの、上限内での消化を時系列で返す。"""
    refill_per_sec = rpm_limit / 60.0
    bucket = float(rpm_limit)      # 初期は満タン（バーストを一気に受けられる分）
    now = 0.0
    timeline: list[dict] = []
    last = 0.0
    for i in range(num_requests):
        # 経過分だけ枠を回復（上限は rpm_limit）
        bucket = min(rpm_limit, bucket + (now - last) * refill_per_sec)
        last = now
        if bucket >= 1.0:
            bucket -= 1.0
            timeline.append({"req": i, "sent_at": round(now, 2), "waited": 0.0})
        else:
            # 枠が空くまで待つ（＝バックオフして再試行）
            wait = (1.0 - bucket) / refill_per_sec
            now += wait
            bucket = 0.0
            last = now
            timeline.append({"req": i, "sent_at": round(now, 2),
                             "waited": round(wait, 2)})
        # 次の到着（バーストなので間隔ゼロで詰めて来る想定）
    total_time = timeline[-1]["sent_at"] if timeline else 0.0
    throttled = sum(1 for t in timeline if t["waited"] > 0)
    return {"timeline": timeline, "total_time_sec": total_time,
            "throttled": throttled, "rpm_limit": rpm_limit}


# --- ROI 試算（本文 15-8）-----------------------------------------------------
# リターン（削減工数×人件費）と、コスト（初期構築＋運用〔従量＋人手〕）の天秤。

@dataclass
class ROIInput:
    reduced_hours_per_month: float   # 月あたり削減できた工数（時間）
    hourly_wage: float               # 人件費（擬似・円/時間 でも $/時間 でも可）
    monthly_token_cost: float        # 月間の従量コスト（15-2 の試算＋判定・保管）
    monthly_human_cost: float        # 監視・評価更新・乗り換え等の人手（本文 15-8）
    initial_cost: float = 0.0        # 初期構築（設計・開発・委託）


def estimate_roi(x: ROIInput) -> dict:
    """月間の見返り・純益・回収期間を返す（本文 15-8）。"""
    monthly_saving = x.reduced_hours_per_month * x.hourly_wage
    monthly_ops = x.monthly_token_cost + x.monthly_human_cost
    net_monthly = monthly_saving - monthly_ops
    payback = (x.initial_cost / net_monthly) if net_monthly > 0 else None
    return {
        "monthly_saving": monthly_saving,
        "monthly_ops_cost": monthly_ops,
        "net_monthly": net_monthly,
        "worth_it": net_monthly > 0,
        "payback_months": (round(payback, 1) if payback is not None else None),
    }
