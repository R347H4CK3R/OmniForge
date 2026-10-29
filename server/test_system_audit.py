import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from scripts.omniforge_system_audit import audit
class SystemAuditTests(unittest.TestCase):
    def test_missing_real_device_evidence_cannot_pass(self):
        with patch("scripts.omniforge_system_audit.check_command",return_value=("PASS","ok")),patch(
            "scripts.omniforge_system_audit.check_tcp",return_value=("PASS","RFB")),patch(
            "scripts.omniforge_system_audit.check_http",return_value=("PASS","HTTP 200")):
            result=audit(Path("."))
        self.assertFalse(result["fully_verified"])
        self.assertEqual(next(x for x in result["results"] if x["name"]=="iPhone zoom/pan and click accuracy")["status"],"NOT_TESTED")
    def test_bridge_failure_is_reported(self):
        with patch("scripts.omniforge_system_audit.check_command",return_value=("PASS","ok")),patch(
            "scripts.omniforge_system_audit.check_tcp",return_value=("FAIL","no service")),patch(
            "scripts.omniforge_system_audit.check_http",return_value=("PASS","HTTP 200")):
            result=audit(Path("."))
        self.assertFalse(result["fully_verified"])
        self.assertEqual(result["results"][2]["status"],"FAIL")
if __name__=="__main__":unittest.main()
