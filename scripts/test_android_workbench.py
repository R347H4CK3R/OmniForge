import io, pathlib, tempfile, unittest, zipfile
from android_workbench import inspect_apk, build_project, artifact_info, extract_project
class AndroidWorkbenchTests(unittest.TestCase):
    def archive(self, entries):
        p=pathlib.Path(self.tmp.name)/'app.apk'
        with zipfile.ZipFile(p,'w') as z:
            for k,v in entries.items(): z.writestr(k,v)
        return p
    def setUp(self): self.tmp=tempfile.TemporaryDirectory()
    def tearDown(self): self.tmp.cleanup()
    def test_artifact_digest_streamed(self):
        p=pathlib.Path(self.tmp.name)/'built.apk';p.write_bytes(b'apk')
        from unittest.mock import patch
        with patch.object(pathlib.Path,'read_bytes',side_effect=AssertionError('whole file read')):
            r=artifact_info(p,pathlib.Path(self.tmp.name))
            self.assertEqual(r['path'],'built.apk');self.assertEqual(len(r['sha256']),64)
    def test_project_zip_traversal_rejected(self):
        with self.assertRaises(ValueError):extract_project(self.archive({'settings.gradle':'','../escape':'x'}),pathlib.Path(self.tmp.name)/'out')
    def test_project_zip_extracted(self):
        out=pathlib.Path(self.tmp.name)/'out';extract_project(self.archive({'settings.gradle':'','app/build.gradle':'// source'}),out)
        self.assertTrue((out/'app/build.gradle').is_file())
    def test_inventory(self):
        r=inspect_apk(self.archive({'AndroidManifest.xml':b'xml','classes.dex':b'dex\n035\0','lib/arm64-v8a/libx.so':b'elf'}))
        self.assertEqual(r['dex_files'],['classes.dex']);self.assertEqual(r['abis'],['arm64-v8a'])
        self.assertFalse(r['original_source_recovered'])
    def test_traversal_rejected(self):
        with self.assertRaises(ValueError): inspect_apk(self.archive({'../escape':'bad'}))
    def test_missing_manifest_rejected(self):
        with self.assertRaises(ValueError): inspect_apk(self.archive({'file':'x'}))
    def test_source_build_requires_project(self):
        with self.assertRaises(ValueError): build_project(pathlib.Path(self.tmp.name))
if __name__=='__main__':unittest.main()
