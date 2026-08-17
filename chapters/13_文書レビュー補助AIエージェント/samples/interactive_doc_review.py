"""自分のテキストを3観点で並列レビューさせる対話スクリプト

※ 本リポジトリ限定の追加教材。書籍本文には登場しません。

13-2_agent_pipeline.py のパイプライン（Supervisor → 3観点Workerの並列実行 →
reducerで集約 → 根拠照合（validate_findings）→ 統合レポート）のノードを
import して使い、レビュー対象をダミー契約書ではなく「自分のテキスト」にする。
テキストはファイルパス指定（--file）か、標準入力への貼り付けで渡す。

2モードで動く。

1. 既定（APIキー不要）:
   Workerは 13-5 と同じ擬似Worker。擬似Workerはキーワード規則
   （「賠償」「催告なく」「別途協議」「問題がなければ検収」「個人情報」「納入する」）
   に反応する決め打ちなので、これらの語を含まないテキストでは指摘0件になる。
   それでも、並列fan-out → reducer集約 → 根拠照合 → 統合という流れは
   自分の文書の行番号・章立てで確かめられる。

2. 本番（任意）:
   環境変数 ANTHROPIC_API_KEY が設定され、anthropic パッケージが入っていれば、
   3観点のWorkerを実際の Claude 呼び出しに差し替え、自由なテキストへの指摘を得る。
   モデルが申告した参照（章・行・抜粋）は 13-6 の根拠照合をそのまま通すので、
   原文と一致しない指摘が「根拠不一致・未確認」に分けられる様子も観察できる。
   （anthropic の導入: pip install anthropic）

実行:
    python interactive_doc_review.py --file 契約書.txt   # ファイルを1回レビュー
    python interactive_doc_review.py                     # 貼り付けモード（空行で確定）

貼り付けモードは空行を入力すると文書の確定になるため、空行を含む文書は
--file で渡すこと。対話は何も貼り付けずに空行（または Ctrl+C）で終了する。

注意:
    モデル名（MODEL）は新しい世代が出るたびに更新される。本番モードで
    not_found_error 等が出たら、Anthropic 公式ドキュメントで現行の
    モデル名を確認して置き換えること。
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import pathlib
import re
import sys

from langgraph.graph import END, START, StateGraph

from _common import pseudo_worker_analyze

# 実行時は公式ドキュメントで最新のモデル名を確認して置き換える
MODEL = "claude-sonnet-4-6"

# ファイル名にハイフンを含むため、13-2 のモジュールはパス指定で読み込む
_here = pathlib.Path(__file__).parent
_spec = importlib.util.spec_from_file_location(
    "agent_pipeline", _here / "13-2_agent_pipeline.py")
_pipeline = importlib.util.module_from_spec(_spec)
# sys.modules に登録してから実行する。未登録だと、State（from __future__ import
# annotations 下の TypedDict）の型ヒントを LangGraph が評価するときに
# モジュールのグローバルを参照できず NameError: 'Annotated' になる
sys.modules[_spec.name] = _pipeline
_spec.loader.exec_module(_pipeline)

DOCUMENT_ID = "user-doc"
DOCUMENT_VERSION = "v1"

VIEWPOINTS = {"法務": "legal_worker", "業務要件": "requirements_worker",
              "技術妥当性": "tech_worker"}

# 「第N条」「第N条(見出し)」「第N条（見出し）」を章の切れ目として拾う
_CHAPTER_RE = re.compile(r"^第[0-9０-９]+条(?:（[^）]*）|\([^)]*\))?")


def to_document(text: str) -> list[dict]:
    """自由テキストを、13章の文書形式（行番号・章つきの行の一覧）に変換する。

    _common.numbered_document() と同じキー構成にすることで、擬似Worker・
    根拠照合（validate_findings）・統合をそのまま流用できる。
    """
    rows: list[dict] = []
    chapter = "本文"
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        m = _CHAPTER_RE.match(line)
        if m:
            chapter = m.group(0)
            line = line[m.end():].strip() or line  # 見出しだけの行は行全体を本文に残す
        rows.append({
            "document_id": DOCUMENT_ID,
            "document_version": DOCUMENT_VERSION,
            "line": len(rows) + 1,
            "chapter": chapter,
            "text": line,
        })
    return rows


# --- Worker実装（差し替え可能）------------------------------------------------
def pseudo_worker(viewpoint: str, document: list[dict]) -> list[dict]:
    """既定：13-5 と同じ擬似Worker（キーワード規則）で自分の文書を走査する。"""
    return pseudo_worker_analyze(viewpoint, document)


def _make_live_worker(client):
    """本番：1観点ぶんの分析を実際の Claude に任せるWorkerを作る。

    返答はJSONで受け取り、参照の検証（文書ID・版・章・行・抜粋の照合）は
    モデルを信用せず 13-6 の validate_findings に任せる。
    """
    def live_worker(viewpoint: str, document: list[dict]) -> list[dict]:
        doc_text = "\n".join(
            f"行{r['line']}: {r['chapter']} {r['text']}" for r in document)
        prompt = (
            f"あなたは文書レビューの{viewpoint}の専門家です。次の行番号付き文書を"
            f"{viewpoint}の観点でレビューし、問題点を挙げてください。\n\n"
            f"# 文書\n{doc_text}\n\n"
            "JSON配列だけを出力してください。各要素は\n"
            '{"chapter": "該当行の章", "line": 行番号(整数), '
            '"excerpt": "該当行の本文をそのまま書き写す", '
            '"issue": "指摘", "severity": "高/中/低"}\n'
            "excerpt は該当行の本文（行頭の章名は含めない）と一字一句同じにしてください。"
            "指摘が無ければ [] を返してください。"
        )
        resp = client.messages.create(
            model=MODEL, max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(b.text for b in resp.content if b.type == "text")
        start, end = text.find("["), text.rfind("]")
        try:
            items = json.loads(text[start:end + 1]) if 0 <= start < end else []
        except json.JSONDecodeError:
            items = []
        if not isinstance(items, list):
            items = []
        if not items:
            print(f"  [メモ] {viewpoint}Workerの指摘は0件（またはJSONとして解釈できず）でした。")
        findings = []
        for it in items:
            if not isinstance(it, dict):
                continue
            chapter = it.get("chapter", "不明")
            excerpt = it.get("excerpt", "")
            # プロンプトでは「行N: 章名 本文」の形で見せているため、モデルが
            # excerpt に章名ごと書き写すことがある。原文の text は章名を含まないので、
            # 行頭の章名だけ確定的に剥がしてから validate_findings の照合に回す
            if chapter != "不明" and excerpt.startswith(chapter):
                excerpt = excerpt[len(chapter):].lstrip()
            findings.append({
                "document_id": DOCUMENT_ID,
                "document_version": DOCUMENT_VERSION,
                "viewpoint": viewpoint,
                "chapter": chapter,
                "line": it.get("line"),
                "excerpt": excerpt,
                "issue": it.get("issue", ""),
                "severity": it.get("severity", "中"),
                "recommendation": "担当者が原文と社内基準を確認する。",
                "status": "要確認",
            })
        return findings

    return live_worker


def build_graph(worker_fn):
    """13-2 と同じグラフを、Workerの実装だけ差し替え可能にして組む。"""
    def make_node(viewpoint: str):
        def node(state):
            return {"findings": worker_fn(viewpoint, state["document"])}
        return node

    b = StateGraph(_pipeline.State)
    b.add_node("supervisor", _pipeline.supervisor_dispatch)
    for viewpoint, node_name in VIEWPOINTS.items():
        b.add_node(node_name, make_node(viewpoint))
    b.add_node("validate", _pipeline.validate)
    b.add_node("integrate", _pipeline.integrate)

    b.add_edge(START, "supervisor")
    for node_name in VIEWPOINTS.values():
        b.add_edge("supervisor", node_name)   # fan-out：3観点を並列実行
        b.add_edge(node_name, "validate")     # fan-in：全Worker完了後に1回だけ
    b.add_edge("validate", "integrate")
    b.add_edge("integrate", END)
    return b.compile()


def _setup_client():
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("[メモ] ANTHROPIC_API_KEY 未設定のため、擬似Worker（キーワード規則）で動きます。")
        return None
    try:
        from anthropic import Anthropic
    except ImportError:
        print("[メモ] anthropic パッケージ未導入のため、擬似Workerで動きます"
              "（本番モードは pip install anthropic）。")
        return None
    return Anthropic()


def review(graph, text: str) -> None:
    document = to_document(text)
    if not document:
        print("テキストが空のため、レビューをスキップします。")
        return
    chapters = list(dict.fromkeys(r["chapter"] for r in document))
    print(f"\n文書 {len(document)}行（章立て: {chapters}）を3観点で並列レビューします。")
    out = graph.invoke({"document": document, "findings": []},
                       {"recursion_limit": 50})
    print(f"  集まった指摘: {len(out['findings'])}件 / "
          f"根拠を確認できた指摘: {len(out['valid_findings'])}件 / "
          f"根拠不一致: {len(out['rejected_findings'])}件")
    print()
    print(out["report"])


def read_pasted() -> str | None:
    """標準入力から貼り付けを受ける。空行で確定。最初から空行なら None（終了）。"""
    print("\nレビューする文書を貼り付けてください（空行で確定。何も貼らずに空行で終了）")
    lines: list[str] = []
    while True:
        try:
            line = input()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not line.strip():
            break
        lines.append(line)
    return "\n".join(lines) if lines else None


def main() -> None:
    parser = argparse.ArgumentParser(
        description="自分のテキストを3観点（法務・業務要件・技術妥当性）で並列レビューする")
    parser.add_argument("--file", help="レビューするテキストファイルのパス（UTF-8）")
    args = parser.parse_args()

    client = _setup_client()
    worker_fn = _make_live_worker(client) if client else pseudo_worker
    graph = build_graph(worker_fn)

    if args.file:
        path = pathlib.Path(args.file)
        if not path.exists():
            print(f"ファイルが見つかりません: {path}")
            sys.exit(1)
        review(graph, path.read_text(encoding="utf-8"))
        return

    while True:
        text = read_pasted()
        if text is None:
            break
        review(graph, text)


if __name__ == "__main__":
    main()
