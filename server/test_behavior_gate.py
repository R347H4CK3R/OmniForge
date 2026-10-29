import json
import tempfile
import unittest
from pathlib import Path
try:
    from behavior_gate import assess
except ImportError:
    from server.behavior_gate import assess

class BehaviorGateTests(unittest.TestCase):
    def test_missing_manifest_is_unverified(self):
        with tempfile.TemporaryDirectory() as d:
            result=assess(d,d)
            self.assertFalse(result["passed"])
            self.assertEqual(result["status"],"UNVERIFIED")
    def test_missing_case_is_failure(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); (p/"acceptance.json").write_text(json.dumps(
                {"requirements":[{"id":"launch"},{"id":"tap"}]}))
            (p/"acceptance-results.json").write_text(json.dumps(
                {"cases":[{"id":"launch","status":"PASS","evidence":"test log"}]}))
            result=assess(p,p)
            self.assertFalse(result["passed"])
            self.assertEqual(result["failed"],["tap"])
    def test_all_explicit_tests_pass(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); (p/"acceptance.json").write_text(json.dumps(
                {"requirements":[{"id":"launch"}]}))
            (p/"acceptance-results.json").write_text(json.dumps(
                {"cases":[{"id":"launch","status":"PASS","evidence":"observed test run"}]}))
            self.assertTrue(assess(p,p)["passed"])
    def test_duplicate_ids_invalid(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); (p/"acceptance.json").write_text(json.dumps(
                {"requirements":[{"id":"a"},{"id":"a"}]}))
            self.assertEqual(assess(p,p)["status"],"INVALID")

if __name__=="__main__": unittest.main()
