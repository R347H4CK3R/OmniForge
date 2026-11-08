import importlib.util
import json
import plistlib
import struct
import tempfile
import unittest
import zipfile
from pathlib import Path

class ArtifactInspectionTests(unittest.TestCase):
    def module(self):
        p=Path(__file__).with_name('inspect_ci_ipas.py')
        self.assertTrue(p.exists(),'artifact inspector missing')
        spec=importlib.util.spec_from_file_location('inspector',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

    def test_reports_actual_app_identity_without_extra_plist_content(self):
        c=self.module()
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'Example.ipa'
            info={'CFBundleIdentifier':'app.example','CFBundleShortVersionString':'1.2','CFBundleVersion':'3','MinimumOSVersion':'17.0','CFBundleExecutable':'App','NeverPrintMe':'private fixture'}
            with zipfile.ZipFile(p,'w') as z:
                z.writestr('Payload/App.app/Info.plist',plistlib.dumps(info))
                z.writestr('Payload/App.app/App',struct.pack('<8I',0xfeedfacf,0x100000c,0,2,1,24,0,0)+struct.pack('<6I',0x32,24,2,17<<16,0,0))
            result=c.inspect_directory(Path(d))
            self.assertEqual(result[0]['bundleIdentifier'],'app.example');self.assertEqual(result[0]['version'],'1.2')
            self.assertNotIn('NeverPrintMe',json.dumps(result));self.assertEqual(len(result[0]['sha256']),64)

    def test_rejects_missing_ipa(self):
        c=self.module()
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):c.inspect_directory(Path(d))

    def test_rejects_symlinked_ipa(self):
        c=self.module()
        with tempfile.TemporaryDirectory() as d:
            (Path(d)/'x.ipa').symlink_to('/etc/passwd')
            with self.assertRaises(ValueError):c.inspect_directory(Path(d))
