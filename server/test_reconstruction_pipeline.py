import importlib.util
import json
import plistlib
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

SCRIPT=Path(__file__).resolve().parents[1]/"scripts"/"reconstruct_ipa_end_to_end.py"
spec=importlib.util.spec_from_file_location("omni_pipeline",SCRIPT)
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class PipelineTests(unittest.TestCase):
    def fixture(self,folder):
        ipa=Path(folder)/"sample.ipa"
        with zipfile.ZipFile(ipa,"w") as archive:
            archive.writestr("Payload/Sample.app/Info.plist",plistlib.dumps({
                "CFBundleExecutable":"Sample","CFBundleIdentifier":"com.example.sample",
                "CFBundleName":"Sample"}))
        return ipa
    def test_no_fake_success_when_only_scaffold_builds(self):
        with tempfile.TemporaryDirectory() as temp:
            ipa=self.fixture(temp); output=Path(temp)/"output"
            report=module.execute(ipa,output,compiler=lambda _:{"passed":True})
            self.assertFalse(report["complete"])
            self.assertFalse(report["functional_equivalence_verified"])
            self.assertEqual(report["stages"]["autonomous_source_implementation"],"NOT_CONFIGURED")
            self.assertTrue((output/"project"/"App"/"ReconstructionApp.swift").is_file())
            self.assertTrue((output/"reconstruction-status.json").is_file())
    def test_invalid_ipa_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            ipa=Path(temp)/"bad.ipa";ipa.write_text("not a zip")
            report=module.execute(ipa,Path(temp)/"out")
            self.assertFalse(report["complete"])
            self.assertIn("error",report)
    def test_missing_ipa_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(ValueError):
                module.execute(Path(temp)/"missing.ipa",Path(temp)/"out")

if __name__=="__main__":unittest.main()
