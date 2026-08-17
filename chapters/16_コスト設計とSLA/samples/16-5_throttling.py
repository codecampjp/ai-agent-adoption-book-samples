"""16-5 レート制限のスロットリング（オフライン）

RPM（1分あたりのリクエスト上限）をトークンバケットで表し、バーストで来た依頼が
枠の空くのを待って再試行され、全体がならされて処理される様子を時系列で見る。
本番では、これが 429＋retry-after の指数バックオフ／流量制御に対応する（本文 16-5）。
"""

from __future__ import annotations

from _common import simulate_throttling


def main():
    num_requests = 12
    rpm_limit = 6       # 1分に6件＝10秒に1件のペースで枠が回復（擬似・小さめで待ちを見せる）

    r = simulate_throttling(num_requests, rpm_limit)
    print(f"=== レート制限 {rpm_limit} RPM に {num_requests} 件がバーストで到着 ===")
    for t in r["timeline"]:
        mark = "" if t["waited"] == 0 else f"（{t['waited']}秒待って再試行）"
        print(f"  req#{t['req']:>2}  送信 t={t['sent_at']:>5}s {mark}")
    print()
    print(f"  上限で待たされた件数 : {r['throttled']} / {num_requests}")
    print(f"  全件さばくのにかかった時間 : {r['total_time_sec']}s")
    print()
    print("※ 最初は満タンの枠でバーストを受け、枠が尽きると待って再試行しならされる。")
    print("※ 速く大量にさばくには上位ティア/並列増だが、それはコスト増（本文 16-5）。")


if __name__ == "__main__":
    main()
