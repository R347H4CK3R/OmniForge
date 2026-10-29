import tempfile
import unittest
from unittest.mock import Mock
try:
    from build_repair import repair_build
except ImportError:
    from server.build_repair import repair_build

class BuildRepairTests(unittest.TestCase):
    def test_repairs_then_reports_actual_pass(self):
        checks=iter([{"exit_code":1,"stderr":"broken"},{"exit_code":0,"stderr":""}])
        agent=Mock(return_value="changed file")
        result=repair_build("fix tests", ".", agent, verify=lambda root, check: next(checks))
        self.assertTrue(result["success"])
        self.assertEqual(len(result["attempts"]),1)
        agent.assert_called_once()
    def test_stops_after_bounded_failures(self):
        agent=Mock(return_value="attempted repair")
        result=repair_build("fix", ".", agent, max_attempts=2,
                            verify=lambda root, check: {"exit_code":1,"stderr":"still broken"})
        self.assertFalse(result["success"])
        self.assertEqual(agent.call_count,2)
    def test_does_not_claim_success_on_agent_error(self):
        def fail(_): raise RuntimeError("model unavailable")
        result=repair_build("fix", ".", fail,
                            verify=lambda root, check: {"exit_code":1,"stderr":"broken"})
        self.assertFalse(result["success"])
        self.assertIn("agent_error",result["attempts"][0])
    def test_reject_unsupported_command(self):
        with self.assertRaises(ValueError):
            repair_build("fix",".",lambda _: None,check="powershell")
if __name__=="__main__": unittest.main()
