"""13-4 deepeval の GEval 設定例（本文 13-4）

※ これは deepeval 公式ドキュメント準拠の「実例」。実行には deepeval のインストールと、
   採点モデル用のAPIキー（例：OPENAI_API_KEY）が要るので、本章のオフラインの
   ドライラン（擬似ジャッジ）とは別枠。実行は次のとおり：
     pip install -U deepeval
     export OPENAI_API_KEY=...          # LLM-as-a-Judge の採点モデル用
     deepeval test run 13-4_deepeval_geval.py

GEval（G-Eval）は LLM-as-a-Judge を道具にしたもの。criteria に観点を言葉で書き、
threshold を割ると assert_test がテストを失敗させる（pytest風・CIにそのまま乗る）。
"""

from deepeval import assert_test
from deepeval.metrics import GEval
from deepeval.test_case import LLMTestCase, LLMTestCaseParams


def run_agent(query: str) -> str:
    """評価対象。本番は第10章のエージェント呼び出しに置き換える（ここは例のスタブ）。"""
    return "該当する記録があります。【出典: OPS-2026-05】"


def test_answer_quality():
    metric = GEval(
        name="正しさ",
        criteria="実際の出力が、該当記録を挙げ出典を添えているか（期待する観点を満たすか）",
        evaluation_params=[
            LLMTestCaseParams.ACTUAL_OUTPUT,
            LLMTestCaseParams.EXPECTED_OUTPUT,
        ],
        threshold=0.5,           # スコアが0.5以上なら合格
    )
    case = LLMTestCase(
        input="先月の障害対応の記録はどこ？",
        actual_output=run_agent("先月の障害対応の記録はどこ？"),
        expected_output="先月の障害対応記録（OPS-2026-05）を、出典つきで案内している",
    )
    assert_test(case, [metric])   # しきい値を割ると、テストが失敗する
