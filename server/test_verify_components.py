import unittest
try:
    from scripts.verify_components import evaluate, COMPONENTS
except ImportError:
    from verify_components import evaluate, COMPONENTS

class VerificationGateTests(unittest.TestCase):
    def test_empty_evidence_never_passes(self):
        r=evaluate({})
        self.assertFalse(r["complete"])
        self.assertTrue(all(x["status"]=="NOT_TESTED" for x in r["checks"]))
    def test_ci_evidence_requires_revision_and_url(self):
        r=evaluate({"checks":{"python_agent_tests":{"status":"PASS","run_url":"https://example.com/test","commit_sha":"abcd1234"}}})
        self.assertEqual(r["checks"][0]["status"],"PASS")
        self.assertFalse(r["complete"])
    def test_device_requires_device_id(self):
        r=evaluate({"checks":{"iphone_controls_windows":{"status":"PASS","run_url":"https://example.com/run",
              "commit_sha":"abcd1234"}}})
        self.assertEqual(next(x for x in r["checks"] if x["component"]=="iphone_controls_windows")["status"],"NOT_TESTED")
    def test_unknown_status_cannot_pass(self):
        r=evaluate({"checks":{"python_agent_tests":{"status":"WORKS"}}})
        self.assertEqual(r["checks"][0]["status"],"NOT_TESTED")

if __name__=="__main__":unittest.main()
