"""3-4 取り出した結果をLLMに渡す（取り込み→検索→生成のプロンプト組み立て）。

本書 3-4 節は「検索で取り出したチャンクを、質問と一緒にプロンプトへ詰めて
LLM に渡す」という生成段階を扱う。本文に API 呼び出しコードは載せていないため、
このサンプルでは次の2モードを用意する。

1. 既定（APIキー不要）:
   3-3 の検索結果をプロンプトに差し込み、組み上がったプロンプトを表示する。
   3-4 本文の「参考文書欄にチャンクを差し込んでモデルに送る」手前までを再現。

2. 生成あり（任意）:
   環境変数 ANTHROPIC_API_KEY が設定され、anthropic パッケージが入っていれば、
   組み立てたプロンプトを実際に Claude へ送って回答を表示する。
   （anthropic の導入: pip install anthropic）

実行:
    python 3-4_rag_with_generation.py
    ANTHROPIC_API_KEY=sk-... python 3-4_rag_with_generation.py   # 生成あり
"""

import os

from importlib import import_module

# 取り込み・検索は 3-3 のものを再利用する
rag_minimal = import_module("3-3_rag_minimal")

PROMPT_TEMPLATE = """\
以下の社内文書を参考に、質問に答えてください。
文書に書かれていないことは「資料からは分かりません」と答えてください。

# 参考文書
{context}

# 質問
{question}
"""


def build_prompt(question: str, chunks: list[str]) -> str:
    context = "\n".join(f"- {c}" for c in chunks)
    return PROMPT_TEMPLATE.format(context=context, question=question)


def generate_with_claude(prompt: str) -> str | None:
    """ANTHROPIC_API_KEY があれば Claude で回答を生成する。なければ None。"""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return None
    try:
        import anthropic
    except ImportError:
        print("[メモ] anthropic 未導入のため生成はスキップ（pip install anthropic）")
        return None

    client = anthropic.Anthropic()
    # モデル名は鮮度メモに従い実行時点の最新を確認すること
    message = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


def main() -> None:
    collection = rag_minimal.build_collection()

    question = "休みを取りたいときの手続きを教えてください。"

    # 検索：質問に近いチャンクを取り出す（ここでは上位2件）
    result = collection.query(query_texts=[question], n_results=2)
    chunks = result["documents"][0]

    prompt = build_prompt(question, chunks)
    print("=== 組み立てたプロンプト ===")
    print(prompt)

    answer = generate_with_claude(prompt)
    if answer is not None:
        print("=== Claude の回答 ===")
        print(answer)
    else:
        print("[メモ] ANTHROPIC_API_KEY 未設定のため、生成は行わずプロンプト表示のみ。")


if __name__ == "__main__":
    main()
