import pathlib,tempfile,unittest
from android_catalog import catalog
class CatalogTests(unittest.TestCase):
    def test_digest_and_version(self):
        with tempfile.TemporaryDirectory() as d:
            p=pathlib.Path(d)/'app.apk';p.write_bytes(b'apk')
            r=catalog(p,7,'https://github.com/R347H4CK3R/OmniForge/releases/download/android-7/OmniForge.apk')
            self.assertEqual(r['versionCode'],7);self.assertEqual(len(r['sha256']),64)
    def test_http_rejected(self):
        with self.assertRaises(ValueError):catalog(pathlib.Path('missing'),1,'http://unsafe.test/app.apk')
if __name__=='__main__':unittest.main()
