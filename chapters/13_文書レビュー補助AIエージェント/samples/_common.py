"""第13章サンプル共通モジュール ── ダミー文書と擬似Worker／擬似モデル

APIキー・ネットワーク不要で章のコードを確かめられるよう、レビュー対象の文書
（業務委託契約書を模したダミー）と、3つの観点（法務／業務要件／技術妥当性）で
分析する擬似Worker、統合レポートを書く擬似Supervisorモデルを、外部依存なしの
純Pythonで用意する。

本文（13-4〜13-6）の骨格に対応する「動く実体」。実運用では、各Workerは
Claude Agent SDK の query() に置き換わり（本文どおり）、Supervisorの統合は
実際のモデル呼び出しになる。ここでは擬似化してオフラインで並列レビューを再現する。
"""

from __future__ import annotations

# --- レビュー対象のダミー文書 -----------------------------------------------
# 各行は (章, 本文) の組。行番号は 1 始まりのリスト添字（+1）で与える。
# Worker は「章・行」で文書内参照を付けられるよう、この行番号を使う。

DOCUMENT_ID = "contract-demo"
DOCUMENT_VERSION = "v1"

DOCUMENT: list[tuple[str, str]] = [
    ("第1条(目的)", "本契約は、甲が乙に委託する業務の内容および条件を定める。"),
    ("第2条(業務内容)", "乙は、甲の受注管理システムの設計・開発業務を行う。"),
    ("第2条(業務内容)", "成果物の詳細な範囲は、別途協議のうえ定めるものとする。"),
    ("第3条(納期・検収)", "乙は、成果物を2026年9月末日までに甲へ納入する。"),
    ("第3条(納期・検収)", "甲は、納入された成果物を確認し、問題がなければ検収する。"),
    ("第4条(委託料)", "甲は、委託料として金500万円（税別）を乙に支払う。"),
    ("第5条(損害賠償)", "乙の責めに帰すべき事由により甲に損害が生じた場合、乙は賠償する。"),
    ("第6条(秘密保持)", "乙は、業務上知り得た甲の秘密情報を第三者に開示してはならない。"),
    ("第6条(秘密保持)", "本システムは顧客の個人情報を取り扱う。"),
    ("第7条(再委託)", "乙は、甲の書面による事前承諾なく業務を再委託してはならない。"),
    ("第8条(契約解除)", "甲は、乙が本契約に違反したときは、催告なく本契約を解除できる。"),
    ("第9条(準拠法)", "本契約は日本法に準拠し、東京地方裁判所を第一審の専属管轄とする。"),
]


def numbered_document() -> list[dict]:
    """文書を「行番号つきの行」の一覧にして返す（章・行で参照できる形）。"""
    return [
        {
            "document_id": DOCUMENT_ID,
            "document_version": DOCUMENT_VERSION,
            "line": i + 1,
            "chapter": ch,
            "text": text,
        }
        for i, (ch, text) in enumerate(DOCUMENT)
    ]


# --- 3観点の擬似Worker -------------------------------------------------------
# 本物の Claude Agent SDK query() の代役。各観点のレビュー規則を決め打ちで持ち、
# 文書を走査して「指摘＋文書内参照（章・行）」を返す。実運用では、この関数の
# 中身が Claude Agent SDK による深い分析（各観点のプロンプト＋MCPツール）に変わる。

# 観点ごとの検査規則：(検出キーワード, 指摘, 重大度)。キーワードを含む行に指摘を付ける。
_RULES: dict[str, list[tuple[str, str, str]]] = {
    "法務": [
        ("賠償", "損害賠償の上限額（キャップ）の定めがなく、乙の負担が青天井になりうる。", "高"),
        ("催告なく", "催告なしの一方的な解除条項。甲のみ解除でき、乙側の救済がない。", "中"),
    ],
    "業務要件": [
        ("別途協議", "成果物の範囲が『別途協議』のままで未確定。着手後の認識齟齬の火種。", "高"),
        ("問題がなければ検収", "検収の合格基準が曖昧。何をもって『問題なし』かの定義がない。", "中"),
    ],
    "技術妥当性": [
        ("個人情報", "個人情報を扱うが、暗号化・アクセス制御などのセキュリティ要件の記載がない。", "高"),
        ("納入する", "可用性・性能（SLA）の数値目標が本文に見当たらない。要確認。", "低"),
    ],
}


def pseudo_worker_analyze(viewpoint: str, document: list[dict]) -> list[dict]:
    """1つの観点で文書を分析し、指摘のリストを返す（Claude Agent SDK Workerの代役）。

    各指摘は viewpoint（観点）／chapter・line（文書内参照）／excerpt（該当箇所の抜粋）
    ／issue（指摘）／severity（重大度）を持つ。
    """
    findings: list[dict] = []
    for rule_kw, issue, severity in _RULES.get(viewpoint, []):
        for row in document:
            if rule_kw in row["text"]:
                findings.append({
                    "document_id": row["document_id"],
                    "document_version": row["document_version"],
                    "viewpoint": viewpoint,
                    "chapter": row["chapter"],
                    "line": row["line"],
                    "excerpt": row["text"],
                    "issue": issue,
                    "severity": severity,
                    "recommendation": "担当者が原文と社内基準を確認する。",
                    "status": "要確認",
                })
                break  # 1規則につき最初の該当行だけを指摘する
    return findings


# --- 擬似Supervisorモデル ----------------------------------------------------
def pseudo_integrate(findings: list[dict], rejected: list[dict] | None = None,
                     worker_errors: list[dict] | None = None) -> str:
    """集まった全指摘を、観点ごとにまとめた統合レポートの文字列にする。

    本文13-6の統合処理の代役。有効な指摘には文書内参照を添え、
    根拠不一致の指摘は未確認事項として分ける。
    """
    worker_errors = worker_errors or []
    rejected = rejected or []
    order = ["法務", "業務要件", "技術妥当性"]
    lines = ["# 文書レビュー統合レポート", ""]
    for vp in order:
        items = [f for f in findings if f["viewpoint"] == vp]
        lines.append(f"## {vp}の観点（{len(items)}件）")
        if any(e["viewpoint"] == vp for e in worker_errors):
            lines.append("- 未確認（Worker失敗のためレビュー未完了）")
        elif not items:
            lines.append("- 根拠未確認の指摘あり" if any(
                f.get("viewpoint") == vp for f in rejected) else "- 指摘なし")
        for f in items:
            ref = f"{f['chapter']} 行{f['line']}"
            lines.append(f"- [{f['severity']}] {f['issue']}（根拠: {ref}「{f['excerpt']}」）")
        lines.append("")
    rejected = rejected or []
    lines.append(f"## 根拠不一致・未確認（{len(rejected) + len(worker_errors)}件）")
    if not rejected and not worker_errors:
        lines.append("- なし")
    for f in rejected:
        lines.append(
            f"- [{f.get('viewpoint', '観点不明')}] "
            f"{f.get('issue', '指摘内容なし')} "
            f"（申告された参照: {f.get('chapter', '不明')} 行{f.get('line', '不明')}）"
        )
    for error in worker_errors:
        lines.append(f"- [{error['viewpoint']}] Worker失敗: {error['reason']}。"
                     f"再実行: {error['retry']}")
    return "\n".join(lines).rstrip()


# --- 参照の照合（本文13-6）--------------------------------------------------
def validate_findings(findings: list[dict], document: list[dict]) -> tuple[list[dict], list[dict]]:
    """各指摘の文書内参照（章・行・抜粋）を、原文と突き合わせて検証する。

    文書ID・版・行・章名が一致し、抜粋が原文に含まれる指摘だけを採用（valid）し、
    どれかが崩れている指摘は不採用（rejected）に回す。モデルが実在しない条項を
    でっち上げても、ここで根拠不一致として分けられる（本文13-6）。
    戻り値は (valid, rejected) の2つのリスト。
    """
    by_line = {row["line"]: row for row in document}
    valid: list[dict] = []
    rejected: list[dict] = []
    for f in findings:
        row = by_line.get(f.get("line"))
        excerpt = f.get("excerpt") or ""
        if (
            row
            and row["document_id"] == f.get("document_id")
            and row["document_version"] == f.get("document_version")
            and row["chapter"] == f.get("chapter")
            and excerpt
            and excerpt in row["text"]
        ):
            valid.append(f)
        else:
            rejected.append(f)
    return valid, rejected
