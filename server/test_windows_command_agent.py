import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
try:
    from windows_command_agent import run
    from agent_server import tool_run
except ImportError:
    from server.windows_command_agent import run
    from server.agent_server import tool_run

class WindowsCommandTests(unittest.TestCase):
    def test_rejects_arbitrary_shell(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):
                run("powershell -EncodedCommand anything",d)
    def test_runs_safe_python_version_or_compile(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            (p/"ok.py").write_text("value=1\n")
            r=run("python_compile",p)
            self.assertEqual(r["exit_code"],0)
            self.assertFalse(r["timed_out"])
    def test_agent_tool_cannot_run_unauthorized_command(self):
        with self.assertRaises(ValueError):
            tool_run("windows_command",{"command":"powershell"})
if __name__=="__main__":
    unittest.main()
