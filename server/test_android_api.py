import pathlib,tempfile,unittest
from android_api import execute
class AndroidAPITests(unittest.TestCase):
    def test_workspace_escape_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):execute(pathlib.Path(d),{'action':'inspect','path':'../private.apk'})
    def test_unknown_action_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):execute(pathlib.Path(d),{'action':'shell','path':'.'})
    def test_android_agent_can_edit_and_read_host_source(self):
        with tempfile.TemporaryDirectory() as d:
            root=pathlib.Path(d)
            execute(root,{'action':'write_file','path':'project/Main.kt','content':'class Main'})
            self.assertEqual(execute(root,{'action':'read_file','path':'project/Main.kt'})['content'],'class Main')
            self.assertIn('Main.kt',execute(root,{'action':'list_files','path':'project'})['files'])
    def test_host_write_cannot_escape(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):execute(pathlib.Path(d),{'action':'write_file','path':'../escape.kt','content':'x'})
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

class AndroidCompletionTests(unittest.TestCase):
    def test_native_agent_owns_tool_loop(self):
        from android_api import complete
        import io,json
        seen={}
        def open_request(req,timeout):
            seen.update(json.loads(req.data));return io.BytesIO(json.dumps({'message':{'content':'{"answer":"ok"}'}}).encode())
        result=complete({'messages':[{'role':'user','content':'hello'}]},'qwen2.5-coder:1.5b',opener=open_request)
        self.assertEqual(result['choices'][0]['message']['content'],'{"answer":"ok"}')
        self.assertNotIn('tools',seen)
        self.assertIn('format',seen)
        self.assertEqual(seen['model'],'qwen2.5-coder:1.5b')
