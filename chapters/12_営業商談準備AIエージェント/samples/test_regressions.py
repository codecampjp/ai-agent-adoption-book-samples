"""APIキー不要。python -m unittest discover -p 'test_*.py' -v"""
import importlib.util
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import _common


def load(filename):
    spec = importlib.util.spec_from_file_location(filename.replace("-", "_"), Path(__file__).with_name(filename))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


class SearchTests(unittest.TestCase):
    def test_unknown_company_stays_unconfirmed_in_both_graphs(self):
        for filename in ("12-2_agent_pipeline.py", "12-5_executor_loop.py"):
            with self.subTest(filename=filename):
                result = load(filename).build_graph().invoke(
                    {"goal": "架空商事 新規提案"},
                    {"configurable": {"thread_id": "unknown"}, "recursion_limit": 50})
                self.assertTrue(all(f["result"]["status"] == "not_found" for f in result["findings"]))
                draft = result.get("draft") or _common.pseudo_synthesize("架空商事", result["findings"])
                self.assertNotEqual(draft["未確認事項と出典"]["未確認事項"], ["なし"])
                self.assertNotIn("新倉庫", json.dumps(draft, ensure_ascii=False))
                self.assertNotIn("見送り理由でした", json.dumps(draft, ensure_ascii=False))

    def test_known_company_keeps_sources(self):
        result = load("12-2_agent_pipeline.py").build_graph().invoke(
            {"goal": "みらい物流 新規提案"},
            {"configurable": {"thread_id": "known"}, "recursion_limit": 50})
        self.assertTrue(all(f["result"]["status"] == "ok" for f in result["findings"]))
        self.assertIn("新倉庫", result["draft"]["準備メモ"])
        self.assertIn("__interrupt__", result)  # 外向き出力の前にHITLで止まる
        self.assertTrue(all(f["result"]["source_id"].startswith("dummy:") for f in result["findings"]))

    def test_errors_are_not_facts(self):
        for exc, status in [(PermissionError(), "forbidden"), (RuntimeError(), "error")]:
            with self.subTest(status=status), patch.object(_common, "web_lookup", side_effect=exc):
                result = _common.search_result("web_search", "みらい物流")
                self.assertEqual(result["status"], status)
                draft = _common.pseudo_synthesize("みらい物流", [{"tool": "web_search", "result": result}])
                self.assertIn("未確認", draft["準備メモ"])

    def test_invalid_tool_response(self):
        for text in ('NOT JSON', '[]', '{"status":"ok","content":[]}', '{"status":"ok","content":[3]}'):
            self.assertEqual(_common.decode_result(text)["status"], "error")

    def test_successful_unrelated_text_does_not_imply_warehouse_or_cost(self):
        findings = [{"tool": t, "result": {"status": "ok", "content": ["初回接触"]}}
                    for t in ("web_search", "crm_search")]
        draft = _common.pseudo_synthesize("別企業", findings)
        self.assertNotIn("新倉庫", json.dumps(draft, ensure_ascii=False))
        self.assertNotIn("見送り理由でした", json.dumps(draft, ensure_ascii=False))

if __name__ == "__main__":
    unittest.main()
