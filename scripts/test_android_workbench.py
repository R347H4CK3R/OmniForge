import io, pathlib, tempfile, unittest, zipfile
from android_workbench import inspect_apk, build_project
class AndroidWorkbenchTests(unittest.TestCase):
    def archive(self, entries):
        p=pathlib.Path(self.tmp.name)/'app.apk'
        with zipfile.ZipFile(p,'w') as z:
            for k,v in entries.items(): z.writestr(k,v)
        return p
    def setUp(self): self.tmp=tempfile.TemporaryDirectory()
    def tearDown(self): self.tmp.cleanup()
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
