import json
import tempfile
import unittest
from pathlib import Path
try:
    from knowledge_vault import KnowledgeVault
except ImportError:
    from server.knowledge_vault import KnowledgeVault

class VaultTest(unittest.TestCase):
    def test_add_and_search(self):
        with tempfile.TemporaryDirectory() as folder:
            vault=KnowledgeVault(Path(folder)/"kb.sqlite3")
            self.assertTrue(vault.add("IPA build","LiveContainer IPA troubleshooting","test"))
            self.assertEqual(len(vault.search("LiveContainer")),1)
    def test_chatgpt_export(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"conversations.json"
            path.write_text(json.dumps([{"title":"Codex Project","mapping":{"one":{"message":{"author":{"role":"user"},"create_time":1,"content":{"parts":["Repair IPA workflow"]}}}}}]),encoding="utf-8")
            vault=KnowledgeVault(Path(folder)/"kb.sqlite3")
            self.assertEqual(vault.import_file(path),1)
            self.assertEqual(vault.search("workflow")[0]["title"],"Codex Project")
    def test_generic_jsonl(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"sessions.jsonl"
            path.write_text(json.dumps({"title":"Tool log","content":"Github Actions test"})+"\n",encoding="utf-8")
            vault=KnowledgeVault(Path(folder)/"kb.sqlite3")
            self.assertEqual(vault.import_file(path),1)
            self.assertEqual(len(vault.search("Github")),1)
if __name__=="__main__": unittest.main()
