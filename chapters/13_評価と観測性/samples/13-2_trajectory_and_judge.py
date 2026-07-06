"""13-2 Trajectory Eval と LLM-as-a-Judge（擬似ジャッジ）でスコアを出す（オフライン）

本文 13-2 の2つの評価法を、擬似エージェント＋擬似ジャッジでオフライン再現する。
  ・Trajectory Eval … 擬似エージェントがたどった道筋（ツール呼び出しの並び）を、
                      期待の道筋と突き合わせる（_common.judge_output の「道筋一致」）
  ・LLM-as-a-Judge  … 出力を「期待する観点」で採点する（擬似ジャッジ＝ルールベースで代役）

本番では、擬似ジャッジを promptfoo の llm-rubric や deepeval の GEval に置き換える。
"""

from __future__ import annotations

from _common import DATASET, pseudo_agent, judge_output


def main():
    print("=== 各ケースを採点（Trajectory Eval ＋ LLM-as-a-Judge の代役）===")
    for case in DATASET:
        output = pseudo_agent(case["input"], case["role"])
        result = judge_output(case, output)

        print(f"\n[{result['id']}] 入力: {case['input']}")
        print(f"  エージェントの回答: {output['answer']}")
        print(f"  たどった道筋      : {' → '.join(output['trajectory'])}")
        print(f"  期待の道筋        : {' → '.join(case['expected']['trajectory'])}")
        for name, ok in result["checks"].items():
            print(f"    - {name}: {'OK' if ok else 'NG'}")
        print(f"  スコア: {result['score']:.2f}")


if __name__ == "__main__":
    main()
