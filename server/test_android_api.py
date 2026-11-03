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
