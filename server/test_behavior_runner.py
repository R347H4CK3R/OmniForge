import hashlib
import json
import tempfile
import unittest
from pathlib import Path
try:
    from behavior_runner import run_probes
    from behavior_gate import assess
except ImportError:
    from server.behavior_runner import run_probes
    from server.behavior_gate import assess

class ExecutedBehaviorTests(unittest.TestCase):
    def test_matching_and_mismatching_evidence(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); project=root/"project"; evidence=root/"evidence"
            project.mkdir(); evidence.mkdir()
            (project/"sample.txt").write_text("expected")
            digest=hashlib.sha256(b"expected").hexdigest()
            (evidence/"acceptance.json").write_text(json.dumps({"requirements":[
                {"id":"correct","type":"file_sha256","path":"sample.txt","sha256":digest},
                {"id":"wrong","type":"file_sha256","path":"sample.txt","sha256":"0"*64}]}))
            result=run_probes(project,evidence)
            self.assertEqual([c["status"] for c in result["cases"]],["PASS","FAIL"])
            self.assertFalse(assess(project,evidence)["passed"])
    def test_outside_workspace_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); project=root/"p"; evidence=root/"e"
            project.mkdir(); evidence.mkdir()
            (evidence/"acceptance.json").write_text(json.dumps({"requirements":[
                {"id":"escape","type":"file_sha256","path":"../e/acceptance.json","sha256":"0"*64}]}))
            result=run_probes(project,evidence)
            self.assertEqual(result["cases"][0]["status"],"FAIL")

if __name__=="__main__": unittest.main()
