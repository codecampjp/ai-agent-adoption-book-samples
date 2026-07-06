"""12-5 Worker層（Claude Agent SDK）── 各観点の深い分析

本文 12-5 に対応。1つの観点（ここでは法務）で文書を分析するWorkerを、
(A) 本番の Claude Agent SDK を使う形（骨格・既定ではオフラインなので動かさない）と
(B) オフラインで動く擬似Worker、の両方で示す。

本番では query() が各観点のプロンプトとツール（MCPなど）でエージェントを自走させ、
文書内参照（章・行）つきの指摘を返す。ここではその代役を擬似Workerが務める。

APIキー・ネットワーク不要（既定は擬似Workerだけを動かす）。
"""

from __future__ import annotations

import os

from _common import numbered_document, pseudo_worker_analyze


# --- (A) 本番：Claude Agent SDK Worker（骨格）--------------------------------
# 実行には claude-agent-sdk のインストールと APIキーが要る。既定では呼ばない。
async def claude_worker_analyze(viewpoint: str, document_text: str) -> str:
    from claude_agent_sdk import query, ClaudeAgentOptions  # pip install claude-agent-sdk

    prompt = (
        f"あなたは契約書レビューの{viewpoint}の専門家です。次の文書を{viewpoint}の観点で"
        f"レビューし、問題点を『章・行』の参照つきで挙げてください。\n\n{document_text}"
    )
    options = ClaudeAgentOptions(system_prompt=f"{viewpoint}レビュー担当", max_turns=1)
    chunks: list[str] = []
    async for message in query(prompt=prompt, options=options):
        chunks.append(str(message))
    return "\n".join(chunks)


# --- (B) オフライン：擬似Worker ---------------------------------------------
def pseudo_worker(viewpoint: str) -> list[dict]:
    """擬似Worker：本番の claude_worker_analyze の代役。指摘を構造化して返す。"""
    return pseudo_worker_analyze(viewpoint, numbered_document())


def main():
    viewpoint = "法務"
    if os.environ.get("USE_CLAUDE_AGENT_SDK"):
        # 本番経路（APIキーが要る）。既定では通らない
        import asyncio
        doc = "\n".join(f"{r['line']}: {r['chapter']} {r['text']}" for r in numbered_document())
        print(asyncio.run(claude_worker_analyze(viewpoint, doc)))
        return

    print(f"=== 擬似{viewpoint}Worker の指摘 ===")
    for f in pseudo_worker(viewpoint):
        print(f"  [{f['severity']}] {f['issue']}")
        print(f"       根拠: {f['chapter']} 行{f['line']}「{f['excerpt']}」")


if __name__ == "__main__":
    main()
