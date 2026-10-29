"""Integration regression tests for the single-entry IPA reconstruction coordinator."""
import json
import plistlib
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch
from scripts.reconstruct_ipa_end_to_end import execute

class OneCommandTests(unittest.TestCase):
    def make_ipa(self, root):
        ipa=Path(root)/"sample.ipa"
        with zipfile.ZipFile(ipa,"w") as archive:
            archive.writestr("Payload/Sample.app/Info.plist",plistlib.dumps({
                "CFBundleIdentifier":"org.example.sample",
                "CFBundleExecutable":"Sample",
                "CFBundleName":"Sample"}))
        return ipa

    def test_scaffold_cannot_claim_completion(self):
        with tempfile.TemporaryDirectory() as folder:
            ipa=self.make_ipa(folder)
            result=execute(ipa,Path(folder)/"output",compiler=lambda _:{"passed":True})
            self.assertFalse(result["complete"])
            self.assertEqual(result["stages"]["project_generation"],"PASS")
            self.assertEqual(result["stages"]["evidence_import"],"NOT_PROVIDED")
            self.assertFalse(result["functional_equivalence_verified"])
            self.assertTrue((Path(folder)/"output"/"reconstruction-status.json").is_file())

    def test_failed_compiler_propagates(self):
        with tempfile.TemporaryDirectory() as folder:
            ipa=self.make_ipa(folder)
            result=execute(ipa,Path(folder)/"output",compiler=lambda _:{"passed":False})
            self.assertFalse(result["complete"])
            self.assertFalse(result["stages"]["compilation"]["passed"])

    def test_missing_input_reports_error(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(ValueError):
                execute(Path(folder)/"missing.ipa",Path(folder)/"output")

if __name__=="__main__": unittest.main()
