"""第11章サンプル共通モジュール ── ダミーの情報源と擬似モデル

APIキー・ネットワーク不要で章のコードを確かめられるよう、商談準備に使う3つの
情報源（公開Web情報・社内CRM・過去案件ログ）を模した小さなダミーデータと、
計画立案・統合を担う擬似モデルを、外部依存なしの純Pythonで用意する。

本文（11-4〜11-7）の骨格に対応する「動く実体」。実運用では、Web検索は既製の
Web検索MCP（Tavily等）、CRMは公式のCRM MCP（Salesforce/HubSpot等）、過去案件は
自社ログのRAG（第3章）に、擬似モデルは実際のモデル呼び出しに置き換わる（本文どおり）。
"""

from __future__ import annotations

# --- ダミーの3つの情報源 -----------------------------------------------------
# 顧客企業「みらい物流」を例に、商談準備の材料を用意する。

WEB_NEWS = {
    "みらい物流": [
        "みらい物流、2026年に新倉庫を稼働。EC向け配送を強化すると発表。",
        "みらい物流、ドライバー不足を背景に配送ルート最適化AIの導入を検討中と報道。",
    ],
}

CRM_RECORDS = {
    "みらい物流": [
        "2025-11 初回接触。倉庫管理システムの刷新に関心。予算は未確定。",
        "2026-03 提案するも見送り（失注理由：初期費用が高い）。関係は継続。",
    ],
}

PAST_CASES = [
    {"id": "case-2024-物流A", "industry": "物流",
     "summary": "配送ルート最適化を月額サブスクで提案し受注。初期費用を抑えた点が決め手。"},
    {"id": "case-2023-製造B", "industry": "製造",
     "summary": "倉庫の在庫可視化を段階導入で提案。まずPoCから入り本導入へつなげた。"},
]

_INDUSTRY_KEYWORDS = {"物流": "物流", "倉庫": "物流", "配送": "物流", "製造": "製造"}


def _company_in(query: str) -> str | None:
    for name in set(WEB_NEWS) | set(CRM_RECORDS):
        if name in query:
            return name
    return None


def web_lookup(query: str) -> list[str]:
    """公開Web情報の検索（Web検索MCPの代役）。企業名を含む記事の抜粋を返す。"""
    company = _company_in(query)
    return WEB_NEWS.get(company, []) if company else []


def crm_lookup(query: str) -> list[str]:
    """社内CRMの検索（CRM MCPの代役）。利用者の権限内という前提で過去のやり取りを返す。"""
    company = _company_in(query)
    return CRM_RECORDS.get(company, []) if company else []


def past_case_lookup(query: str) -> list[dict]:
    """過去案件ログの検索（自社RAGの代役）。業種キーワードで類似事例を返す（出典id付き）。"""
    industries = {v for k, v in _INDUSTRY_KEYWORDS.items() if k in query}
    hits = [c for c in PAST_CASES if c["industry"] in industries]
    return hits or PAST_CASES[:1]


# --- 擬似モデル ---------------------------------------------------------------
# 本物のLLMの代役。計画立案と最終統合を、決め打ちのロジックで再現する。

def pseudo_plan(goal: str) -> list[dict]:
    """Plannerの代役：ゴールから調査ステップの並びを作る（本文 11-4）。

    各ステップは、実行時に呼ぶ道具（tool）と引数（arg）を持つ。実運用では、
    この並びをモデルが立てる。
    """
    company = _company_in(goal) or goal.strip()
    return [
        {"desc": f"{company}の直近ニュースをWebで調べる",
         "tool": "web_search", "arg": f"{company} 最新 ニュース 倉庫 配送"},
        {"desc": f"{company}との過去のやり取りをCRMで確認する",
         "tool": "crm_search", "arg": f"{company} 過去 案件 やり取り"},
        {"desc": f"{company}と似た業種への過去提案を探す",
         "tool": "past_case_search", "arg": "物流 倉庫 配送 の過去提案"},
    ]


def pseudo_synthesize(goal: str, findings: list[dict]) -> dict:
    """Synthesizerの代役：集めた findings を3部構成のドラフトに束ねる（本文 11-7）。

    材料に無いことは推測で埋めず「未確認」とする方針を、コードで再現する。
    """
    def _texts(tool: str) -> list[str]:
        out: list[str] = []
        for f in findings:
            if f["tool"] == tool:
                out.extend(f["result"] if isinstance(f["result"], list) else [str(f["result"])])
        return out

    web = _texts("web_search")
    crm = _texts("crm_search")
    cases = _texts("past_case_search")

    memo = "／".join(web) if web else "未確認（Web情報を取得できず）"
    if crm:
        memo += "。過去の経緯：" + "／".join(crm)

    questions = [
        "初期費用の負担感が見送り理由でしたが、月額型なら検討余地はありますか？" if crm else "ご予算とご要望の優先順位を教えてください。",
        "新倉庫の稼働に合わせて、配送の課題で急ぎのものはありますか？" if web else "現在いちばんお困りの業務は何でしょうか？",
    ]

    proposal = "提案骨子：" + ("／".join(cases) if cases else "未確認（類似案件が見つからず）")

    return {"準備メモ": memo, "想定質問": questions, "提案骨子": proposal}
