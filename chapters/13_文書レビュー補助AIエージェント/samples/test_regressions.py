"""APIを呼ばずに応答失敗と元文書の行番号を検証する。"""
import json
from types import SimpleNamespace
import unittest
import interactive_doc_review as review


def client(text, stop_reason="end_turn"):
    return SimpleNamespace(messages=SimpleNamespace(create=lambda **kwargs:
        SimpleNamespace(stop_reason=stop_reason, content=[SimpleNamespace(type="text", text=text)])))


def run(worker):
    return review.build_graph(worker).invoke({"document": review.to_document("本文"), "findings": [], "worker_errors": []})


class ReviewTests(unittest.TestCase):
    def test_blank_lines_preserve_original_line_numbers(self):
        rows = review.to_document("第1条(目的)\n\n本文\n\n末尾")
        self.assertEqual([r["line"] for r in rows], [1, 3, 5])
        self.assertEqual(rows[1]["chapter"], "第1条(目的)")

    def test_empty_success_is_distinct_from_failure(self):
        out = run(review._make_live_worker(client("[]")))
        self.assertEqual(out["worker_errors"], [])
        self.assertEqual(out["report"].count("指摘なし"), 3)

    def test_invalid_and_truncated_responses_stay_unconfirmed(self):
        for text, reason in [("NOT JSON", "end_turn"), ("{}", "end_turn"),
                             ("[3]", "end_turn"), ('[{"issue":"x"}]', "end_turn"),
                             ("[]", "max_tokens"), ("[]", "refusal")]:
            with self.subTest(text=text, reason=reason):
                out = run(review._make_live_worker(client(text, reason)))
                self.assertEqual(len(out["worker_errors"]), 3)
                self.assertNotIn("指摘なし", out["report"])
                self.assertIn("再実行", out["report"])

    def test_one_failure_preserves_other_viewpoints(self):
        def worker(viewpoint, document):
            if viewpoint == "法務":
                raise TimeoutError("secret response must not be printed")
            return []
        out = run(worker)
        self.assertEqual(len(out["worker_errors"]), 1)
        self.assertEqual(out["report"].count("指摘なし"), 2)
        self.assertNotIn("secret response", out["report"])

    def test_valid_and_fabricated_references(self):
        for line, valid in [(1, True), (99, False)]:
            text = json.dumps([{"chapter": "本文", "line": line, "excerpt": "本文", "issue": "要確認", "severity": "中"}])
            out = run(review._make_live_worker(client(text)))
            self.assertEqual(len(out["valid_findings"]), 3 if valid else 0)
            self.assertEqual(len(out["rejected_findings"]), 0 if valid else 3)
            self.assertNotIn("指摘なし", out["report"])

if __name__ == "__main__":
    unittest.main()
