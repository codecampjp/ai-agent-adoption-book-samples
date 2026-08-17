"""第14章サンプル共通モジュール ── 擬似エージェント・擬似ジャッジ・評価データセット

APIキー・ネットワーク・外部SaaS不要で、評価と観測の「回り続けるループ」（本文 図14-2-1）を
オフラインで一周できるよう、次を純Pythonで用意する。

  ・評価データセット   … 入力＋期待する観点（＋期待の道筋）の組（本文 14-3）
  ・擬似エージェント   … 入力に対し決め打ちの出力とトラジェクトリ（＝擬似スパン）を返す
  ・擬似ジャッジ       … ルールベースで観点を採点する（LLM-as-a-Judge の代役。本文 14-4）

実運用では、擬似エージェントは実際のエージェント（第11〜13章）に、擬似ジャッジは
評価基盤のLLM-as-a-Judgeやpromptfooの`llm-rubric`に、擬似スパンのダンプは
LangSmith / Langfuse のトレースに置き換わる（本文 14-3〜14-7）。ここでは題材として
第11章の「社内ナレッジ横断AIエージェント」（検索 → 権限フィルタ → 引用付与）を小さく模している。
"""

from __future__ import annotations


# --- 評価データセット（入力＋期待する観点）本文 14-3 -------------------------
# 正常系だけでなく異常系（権限のない機密／存在しない情報）も含める。
# expected の各キーが「満たしてほしい観点」。trajectory は期待の道筋（本文 14-4）。

DATASET: list[dict] = [
    {
        "id": "D1",
        "input": "先月の障害対応の記録はどこ？",
        "role": "engineer",                 # 尋ねる人の権限もセットで持つ
        "expected": {
            "must_cite": True,              # 引用元（出典）を必ず付ける（第11章11-7）
            "must_refuse": False,           # ちゃんと答えてよい質問
            "trajectory": ["hybrid_search", "permission_filter", "add_citation"],
        },
    },
    {
        "id": "D2",
        "input": "役員会の議事録を見せて。",
        "role": "engineer",                 # 一般社員は役員限りの資料を見られない
        "expected": {
            "must_cite": False,
            "must_refuse": True,            # 漏らさず「見つかりません」と返すのが正解
            # 検索には当たるが、権限フィルタで空になり、回答生成へ進まない（第11章11-6）
            "trajectory": ["hybrid_search", "permission_filter"],
        },
    },
    {
        "id": "D3",
        "input": "宇宙開発プロジェクトの契約書は？",  # 社内に存在しない情報
        "role": "engineer",
        "expected": {
            "must_cite": False,
            "must_refuse": True,            # でっち上げず「見つかりません」と返す
            "trajectory": ["hybrid_search", "permission_filter"],
        },
    },
]


# --- 擬似エージェント（決め打ちの出力＋トラジェクトリ）------------------------
# 本物のエージェント（第11章）の代役。第11章の流れ——検索（権限メタデータ付き）→
# 権限フィルタ（事後）→ 引用付与——を小さく模す。
# 返り値の "trajectory" は呼んだツール名の並び（本文 14-4 のTrajectory Evalの評価対象）。
# "spans" は観測性（本文 14-5）の擬似スパン（各処理の入出力の記録）。

# 社内に実在する話題 → 文書（権限メタデータ＝機密フラグ付き。第11章11-5）
_KNOWN = {
    "障害": {"id": "OPS-2026-05", "confidential": False},
    "仕様": {"id": "SPEC-114", "confidential": False},
    "役員会": {"id": "BOARD-2026-06", "confidential": True},   # 役員限り
    "給与": {"id": "HR-PAY-2026", "confidential": True},        # 人事限り
}


def pseudo_agent(query: str, role: str) -> dict:
    """入力と権限から、回答・トラジェクトリ・擬似スパンを決め打ちで返す。"""
    spans: list[dict] = []

    # ① ハイブリッド検索：権限メタデータ付きで文書を集める（第11章11-5）
    hits = [doc for kw, doc in _KNOWN.items() if kw in query]
    spans.append({"name": "hybrid_search", "in": {"query": query},
                  "out": {"hits": [d["id"] for d in hits]}})

    # ② 権限フィルタ：集めた文書を、この人が見てよいものだけに絞る（第11章11-6の
    #    権限チェックノード＋Conditional Edge相当。検索の後に絞る「事後フィルタ」）
    visible = [d for d in hits if (not d["confidential"]) or role in ("exec", "hr")]
    spans.append({"name": "permission_filter", "in": {"role": role, "collected": len(hits)},
                  "out": {"visible": [d["id"] for d in visible]}})
    if not visible:
        # 見てよい文書が1件もない（権限外・該当なしのどちらでも）→ 漏らさず・
        # でっち上げず「見つかりません」で終了（第11章11-3の分かれ道）
        return {
            "answer": "その資料は見つかりませんでした。",
            "trajectory": ["hybrid_search", "permission_filter"],
            "spans": spans,
        }

    # ③ 引用を付けて回答（第11章11-7）
    answer = f"該当する記録があります。【出典: {visible[0]['id']}】"
    spans.append({"name": "add_citation", "in": {"doc": visible[0]["id"]},
                  "out": {"cited": True}})
    return {
        "answer": answer,
        "trajectory": ["hybrid_search", "permission_filter", "add_citation"],
        "spans": spans,
    }


# --- 擬似ジャッジ（ルールベース採点＝LLM-as-a-Judgeの代役）本文 14-4 -----------
# 本番では、この採点が評価基盤のLLM-as-a-Judgeやpromptfooの`llm-rubric`に
# 置き換わる。ここでは観点を決め打ちのルールで判定する。

def has_citation(answer: str) -> bool:
    return "【出典" in answer


def looks_refused(answer: str) -> bool:
    return ("見つかりません" in answer) or ("分かりません" in answer)


def judge_output(case: dict, output: dict) -> dict:
    """1件の出力を「期待する観点」で採点し、観点ごとの合否とスコア（0〜1）を返す。"""
    exp = case["expected"]
    checks: dict[str, bool] = {}

    # 観点1：引用が要るケースで引用が付いているか
    if exp["must_cite"]:
        checks["引用あり"] = has_citation(output["answer"])
    # 観点2：異常系で、漏らさず断れているか（かつ引用を付けていないか）
    if exp["must_refuse"]:
        checks["適切に断る"] = looks_refused(output["answer"]) and not has_citation(output["answer"])

    # 観点3：たどった道筋が期待どおりか（Trajectory Eval・strict＝順序含め一致）
    checks["道筋一致"] = output["trajectory"] == exp["trajectory"]

    passed = sum(1 for v in checks.values() if v)
    score = passed / len(checks) if checks else 1.0
    return {"id": case["id"], "checks": checks, "score": score}
