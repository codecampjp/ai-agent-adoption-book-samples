"""15-6 監査ログの設計 ── 一連の判断を監査ログ1件にまとめて書き出す（オフライン）

多層防御パイプライン（入力ガード→権限スコープ→出力ガード→HITL判定）を1件の依頼に
通し、「誰が・何を・どの関所がどう判断したか」を監査ログ1件として出力する。
本番では、これを改ざん耐性のある監査ログ基盤や SIEM に送ると読み替える。
"""

from __future__ import annotations

import json

from _common import run_pipeline, REQUESTS


def main():
    print("=== 監査ログ（多層防御の判断を1件にまとめる）===\n")
    for req in REQUESTS:
        log = run_pipeline(req)
        # 監査ログはPIIをマスクした形で残す（本文 15-5 / 15-6）
        print(json.dumps(log, ensure_ascii=False, indent=2))
        print("-" * 60)


if __name__ == "__main__":
    main()
