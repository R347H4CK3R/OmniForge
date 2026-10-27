import json
from contextlib import closing
import tempfile
import unittest
from pathlib import Path
try:
    from self_test import run_self_test
except ImportError:
    from server.self_test import run_self_test

class TestSelfTest(unittest.TestCase):
    def test_report_structure_and_workspace(self):
        with tempfile.TemporaryDirectory() as temp:
            result=run_self_test(Path(temp),"http://127.0.0.1:1","unavailable")
            self.assertEqual(result["schema"],1)
            checks={check["name"]:check for check in result["checks"]}
            self.assertEqual(checks["workspace"]["status"],"PASS")
            self.assertEqual(checks["knowledge_database"]["status"],"SKIP")
            self.assertEqual(checks["ollama_model"]["status"],"FAIL")
            self.assertEqual(result["overall"],"FAIL")
    def test_database_integrity(self):
        import sqlite3
        with tempfile.TemporaryDirectory() as temp:
            db=Path(temp)/".omniforge-private"
            db.mkdir()
            with closing(sqlite3.connect(db/"knowledge.sqlite3")) as conn:
                conn.execute("CREATE TABLE example (id INTEGER)")
            report=run_self_test(temp,"http://127.0.0.1:1","missing")
            self.assertEqual(next(c for c in report["checks"] if c["name"]=="knowledge_database")["status"],"PASS")
if __name__=="__main__": unittest.main()
