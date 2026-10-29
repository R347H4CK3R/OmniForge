import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock
try:
    from autonomous_reconstruction import reconstruct, evidence_summary
except ImportError:
    from server.autonomous_reconstruction import reconstruct, evidence_summary

class ReconstructionTests(unittest.TestCase):
    def test_compiler_failure_then_repair_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            project=Path(tmp)/"project"; (project/"App").mkdir(parents=True)
            (project/"project.yml").write_text("name: Reconstruction")
            evidence=Path(tmp)/"evidence"; evidence.mkdir()
            (evidence/"pseudocode_arm64.c").write_text("int sample() { return 1; }")
            responses=iter([{"passed":False},{"passed":True}])
            agent=Mock(return_value="Updated ContentView.swift")
            report=reconstruct(project,evidence,agent,verify=lambda _:next(responses))
            self.assertTrue(report["compiled"])
            self.assertFalse(report["functional_equivalence"])
            self.assertEqual(agent.call_count,1)
            self.assertIn("sample",agent.call_args.args[0])
    def test_no_false_claim_for_existing_compilable_scaffold(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp); (p/"App").mkdir(); (p/"project.yml").write_text("name: Reconstruction")
            agent=Mock()
            report=reconstruct(p,p,agent,verify=lambda _:{"passed":True})
            self.assertTrue(report["compiled"])
            self.assertFalse(report["functional_equivalence"])
            agent.assert_called_once()
    def test_bounded_failures(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp); (p/"App").mkdir(); (p/"project.yml").write_text("name: Reconstruction")
            agent=Mock(return_value="attempt")
            report=reconstruct(p,p,agent,max_repairs=1,verify=lambda _:{"passed":False})
            self.assertFalse(report["compiled"])
            self.assertEqual(agent.call_count,2)
    def test_missing_project_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                reconstruct(tmp,tmp,lambda _: None)

if __name__=="__main__": unittest.main()
