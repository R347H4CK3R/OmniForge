import pathlib,tempfile,unittest
from android_api import execute
class AndroidAPITests(unittest.TestCase):
    def test_workspace_escape_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):execute(pathlib.Path(d),{'action':'inspect','path':'../private.apk'})
    def test_unknown_action_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):execute(pathlib.Path(d),{'action':'shell','path':'.'})
    def test_missing_tool_is_failure(self):
        with tempfile.TemporaryDirectory() as d:
            pathlib.Path(d,'settings.gradle').write_text('')
            result=execute(pathlib.Path(d),{'action':'build','path':'.'})
            self.assertIn('built',result)
if __name__=='__main__':unittest.main()

class AndroidArtifactTests(unittest.TestCase):
    def test_download_cannot_escape_workspace(self):
        from android_api import download_path
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):download_path(d,'../outside.apk')
    def test_non_apk_download_rejected(self):
        from android_api import download_path
        with tempfile.TemporaryDirectory() as d:
            pathlib.Path(d,'secret.txt').write_text('secret')
            with self.assertRaises(ValueError):download_path(d,'secret.txt')
    def test_existing_apk_allowed(self):
        from android_api import download_path
        with tempfile.TemporaryDirectory() as d:
            p=pathlib.Path(d,'sample.apk');p.write_bytes(b'apk')
            self.assertEqual(download_path(d,'sample.apk'),p)
