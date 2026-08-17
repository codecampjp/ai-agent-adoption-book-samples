"""15-7 HITLの発動条件 ── しきい値超過を人へ上げる（オフライン）

危険度スコアを積み上げ、しきい値超過または不可逆操作なら人間の承認へエスカレーションする。
本番では、これを LangGraph の interrupt（第12章）や承認ワークフローに置き換える。
"""

from __future__ import annotations

from _common import run_pipeline, REQUESTS, HITL_THRESHOLD


def main():
    print(f"=== HITL エスカレーション判定（しきい値={HITL_THRESHOLD}）===")
    for req in REQUESTS:
        log = run_pipeline(req)
        route = "→ HITL（人間の承認）へ" if log["escalated_to_hitl"] else "→ 自動で応答"
        print(f"  [{log['id']}] risk={log['risk_score']} {route}")
        reasons = []
        if log["input"]["injection_blocked"]:
            reasons.append("インジェクション疑い")
        if log["input"]["external"]["injection_blocked"]:
            reasons.append("外部データ内の命令（間接インジェクション）")
        if log["tool"]["denied"]:
            reasons.append("許可外ツール")
        if log["tool"]["irreversible"]:
            reasons.append("不可逆操作")
        if log["output"]["masked"]:
            reasons.append("出力に機密/PII")
        if reasons:
            print(f"        理由: {', '.join(reasons)}")


if __name__ == "__main__":
    main()
