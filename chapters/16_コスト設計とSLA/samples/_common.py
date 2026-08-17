"""第16章サンプル共通モジュール ── コスト設計とサービス品質

APIキー・ネットワーク・外部ライブラリ不要で、本章のコスト設計を手元で回せるよう、
次を純Python（標準ライブラリのみ）で用意する。

  ・トークンコストの試算   … 入力/出力/ツール往復/判定分を積み上げ、月間へ（本文 16-1 / 16-2）
  ・プロンプトキャッシュ    … ヒット率でコストがどう変わるかのシミュレーション（本文 16-4）
  ・レート制限のスロットリング … 上限超過を待って再試行し、全体をならす（本文 16-5）
単価表は本文の表16-1-1と同じ2026年7月29日時点のスナップショット。
本番では最新の公式料金と API レスポンスの usage に置き換える。
"""

from __future__ import annotations

from dataclasses import dataclass

# --- 料金スナップショット（米ドル／100万トークン、2026-07-29）-----------------

PRICING: dict[str, dict[str, float]] = {
    "gpt-5.6-luna": {
        "input": 1.0, "output": 6.0, "cache_write": 1.25, "cache_read": 0.10
    },
    "gpt-5.6-terra": {
        "input": 2.5, "output": 15.0, "cache_write": 3.125, "cache_read": 0.25
    },
}

PER_MTOK = 1_000_000


def _cost(tokens: int, price_per_mtok: float) -> float:
    """トークン数 × 100万トークンあたり単価。"""
    return tokens / PER_MTOK * price_per_mtok


# --- 1リクエストのトークン内訳（本文 16-2）------------------------------------
# 入力・出力に加え、ツール往復ぶん・ガードレール/ジャッジの判定ぶんも積み上がる。

@dataclass
class RequestTokens:
    input_tokens: int
    output_tokens: int
    cached_input_tokens: int = 0


def estimate_request_cost(rt: RequestTokens, model: str) -> dict:
    """利用者の1依頼を完了するまでの合計コストを返す。"""
    p = PRICING[model]
    breakdown = {
        "input": _cost(rt.input_tokens, p["input"]),
        "cached_input": _cost(rt.cached_input_tokens, p["cache_read"]),
        "output": _cost(rt.output_tokens, p["output"]),
    }
    breakdown["total_per_request"] = sum(breakdown.values())
    breakdown["model"] = model
    return breakdown


def monthly_cost(per_request_cost: float, monthly_requests: int) -> float:
    """月間コスト。per_request_costには内部の全モデル呼び出しを含める。"""
    return per_request_cost * monthly_requests


# --- プロンプトキャッシュのヒット率シミュレーション（本文 16-4）----------------
# 変わらない「前置き」(prefix) を再利用する。キャッシュ無しでは毎回 input 単価、
# キャッシュ有りでは初回など未ヒット分は書き込み単価、ヒット分は読み出し単価。

def simulate_cache(prefix_tokens: int, requests: int, hit_rate: float,
                   model: str = "gpt-5.6-luna") -> dict:
    """前置き部分について、キャッシュ無し/有りの入力コストを比べる（本文 16-4）。

    hit_rate … 0.0〜1.0。前置きがキャッシュにヒットする割合。
    """
    if not 0.0 <= hit_rate <= 1.0:
        raise ValueError("hit_rate は 0.0〜1.0")
    p = PRICING[model]
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


# --- レート制限のスロットリング（本文 16-5）-----------------------------------
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

