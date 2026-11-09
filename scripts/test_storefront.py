import copy
import json
import unittest
from pathlib import Path
from unified_catalog import render_store_guide

class StorefrontTests(unittest.TestCase):
    def test_guide_has_discovery_and_galleries(self):
        source=json.loads(Path('unified-source.json').read_text())
        original=copy.deepcopy(source)
        rendered=render_store_guide(source)
        self.assertIn('Explore the collection', rendered)
        self.assertIn('Preview coming soon', rendered)
        self.assertIn('Screenshots', rendered)
        self.assertEqual(source,original)

    def test_web_storefront_escapes_content_and_keeps_downloads(self):
        import storefront
        source=json.loads(Path('unified-source.json').read_text())
        source['apps'][0]['name']='<script>alert(1)</script>'
        original=copy.deepcopy(source)
        rendered=storefront.render_storefront(source)
        self.assertIn('&lt;script&gt;',rendered)
        self.assertNotIn('<script>alert(1)</script>',rendered)
        for app in source['apps']:
            self.assertIn(app['versions'][0]['downloadURL'],rendered)
        self.assertIn('id="search"',rendered)
        self.assertEqual(source,original)

    def test_rendered_release_notes_survive_text_file_round_trip(self):
        import tempfile
        from storefront import render_storefront
        source=json.loads(Path('unified-source.json').read_text())
        source['apps'][0]['versions'][0]['localizedDescription']='First line\r\n\r\nSecond line\rThird line'
        original=copy.deepcopy(source)
        for render in (render_storefront, render_store_guide):
            with self.subTest(renderer=render.__name__), tempfile.TemporaryDirectory() as directory:
                path=Path(directory)/'rendered.txt'
                rendered=render(source)
                self.assertIn('First line\n\nSecond line\nThird line',rendered)
                path.write_text(rendered)
                self.assertEqual(path.read_text(),render(source))
        self.assertEqual(source,original)

