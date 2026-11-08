import copy
import importlib.util
import plistlib
import tempfile
import unittest
import zipfile
from pathlib import Path

MODULE = Path(__file__).with_name('unified_catalog.py')

class CatalogTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(MODULE.exists(), 'catalog implementation is missing')
        spec = importlib.util.spec_from_file_location('catalog', MODULE)
        self.c = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.c)

    def archive(self, directory, **overrides):
        p = Path(directory)/'app.ipa'
        info = {'CFBundleIdentifier':'com.example.app', 'CFBundleShortVersionString':'1.0.156',
                'CFBundleVersion':'156', 'CFBundleExecutable':'Example', 'MinimumOSVersion':'17.0'}
        info.update(overrides)
        with zipfile.ZipFile(p, 'w') as z:
            z.writestr('Payload/Example.app/Info.plist', plistlib.dumps(info))
            z.writestr('Payload/Example.app/Example', __import__('struct').pack('<8I',0xfeedfacf,0x100000c,0,2,1,24,0,0) + __import__('struct').pack('<6I',0x32,24,2,0,0,0))
        return p

    def test_reads_real_versions_without_arithmetic(self):
        with tempfile.TemporaryDirectory() as d:
            info = self.c.inspect_ipa(self.archive(d), 'com.example.app')
            self.assertEqual(info['version'], '1.0.156')
            self.assertEqual(info['buildVersion'], '156')

    def test_rejects_wrong_bundle(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):
                self.c.inspect_ipa(self.archive(d), 'com.other.app')

    def test_rejects_missing_executable(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):
                self.c.inspect_ipa(self.archive(d, CFBundleExecutable='Missing'), 'com.example.app')

    def test_rejects_non_arm64_executable(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'bad.ipa'
            good=self.archive(d)
            with zipfile.ZipFile(good) as original:
                plist=original.read('Payload/Example.app/Info.plist')
            with zipfile.ZipFile(p,'w') as z:
                z.writestr('Payload/Example.app/Info.plist',plist)
                z.writestr('Payload/Example.app/Example',b'\xcf\xfa\xed\xfe'+b'\x07\0\0\x01'+b'\0'*24)
            with self.assertRaises(ValueError): self.c.inspect_ipa(p,'com.example.app')

    def test_rejects_simulator_platform(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):
                self.c.inspect_ipa(self.archive(d, CFBundleSupportedPlatforms=['iPhoneSimulator'], DTPlatformName='iphonesimulator'), 'com.example.app')

    def test_rejects_multiple_app_payloads(self):
        with tempfile.TemporaryDirectory() as d:
            p=self.archive(d)
            with zipfile.ZipFile(p, 'a') as z: z.writestr('Payload/Other.app/Info.plist', b'bad')
            with self.assertRaises(ValueError): self.c.inspect_ipa(p, 'com.example.app')

    def test_rejects_non_immutable_or_external_downloads(self):
        for url in ['https://example.com/app.ipa','https://github.com/a/b/releases/latest/download/app.ipa','http://github.com/a/b/releases/download/v1/a.ipa']:
            with self.assertRaises(ValueError): self.c.release_coordinates(url, 'a/b')
        self.assertEqual(self.c.release_coordinates('https://github.com/a/b/releases/download/v1/a.ipa','a/b'), ('v1','a.ipa'))

    def test_rejects_private_draft_missing_or_wrong_size_release(self):
        asset={'name':'a.ipa','size':20,'state':'uploaded','browser_download_url':'https://github.com/a/b/releases/download/v1/a.ipa'}
        release={'draft':False,'prerelease':False,'tag_name':'v1','assets':[asset]}
        self.c.verify_release(release,asset['browser_download_url'],20,False)
        for change in [{'draft':True},{'prerelease':True},{'assets':[]},{'assets':[dict(asset,size=21)]}]:
            with self.assertRaises(ValueError): self.c.verify_release(dict(release,**change),asset['browser_download_url'],20,False)

    def test_preserves_last_good_on_failure(self):
        old={'apps':[{'bundleIdentifier':'com.example.app','versions':[{'version':'1.0','buildVersion':'10'}]}]}
        def fail(_): raise ValueError('bad artifact')
        result, errors=self.c.refresh(old,[{'bundleIdentifier':'com.example.app'}],fail)
        self.assertEqual(result['apps'],old['apps'])
        self.assertEqual(len(errors),1)

    def test_rejects_duplicate_registry(self):
        with self.assertRaises(ValueError):
            self.c.refresh({'apps':[]},[{'bundleIdentifier':'a'},{'bundleIdentifier':'a'}],lambda _: {})

    def test_prevents_older_version_replacement(self):
        old={'apps':[{'bundleIdentifier':'a','versions':[{'version':'1.0.156','buildVersion':'156'}]}]}
        new={'bundleIdentifier':'a','versions':[{'version':'1.0.94','buildVersion':'94'}]}
        result,errors=self.c.refresh(old,[{'bundleIdentifier':'a'}],lambda _:new)
        self.assertEqual(result['apps'],old['apps'])
        self.assertEqual(len(errors),1)

    def test_accepts_higher_marketing_version_lower_build(self):
        old={'apps':[{'bundleIdentifier':'a','versions':[{'version':'1.0','buildVersion':'156'}]}]}
        new={'bundleIdentifier':'a','versions':[{'version':'2.0','buildVersion':'1'}]}
        result,errors=self.c.refresh(old,[{'bundleIdentifier':'a'}],lambda _:new)
        self.assertEqual(result['apps'],[new]); self.assertEqual(errors,[])

if __name__ == '__main__': unittest.main()

class EvidenceTests(unittest.TestCase):
    def test_evidence_requires_passes_and_binary_identity(self):
        import unified_catalog as c
        proof={'inspection':{'archive':'passed','bundleIdentifier':'a','version':'1','build':'2'},
               'nativeDiagnosticSpeechPassed':True,'nativeSimulatorConversionPassed':True,
               'ipaSHA256':'abc','ipaBytes':20}
        actual={'version':'1','buildVersion':'2'}
        c.verify_character_evidence(proof,'a',actual,'abc',20)
        for key,value in [('nativeDiagnosticSpeechPassed',False),('ipaSHA256','wrong'),('ipaBytes',21)]:
            bad=copy.deepcopy(proof); bad[key]=value
            with self.assertRaises(ValueError): c.verify_character_evidence(bad,'a',actual,'abc',20)

class PublicMetadataTests(unittest.TestCase):
    def test_upstream_screenshots_and_unknown_fields_are_not_republished(self):
        import unified_catalog as c
        src={'name':'App','bundleIdentifier':'a','developerName':'D','localizedDescription':'What it does',
             'screenshots':['https://private.example/image.png'],'unknown':'private','appPermissions':{'privacy':{'bad':'value'}},
             'iconURL':'https://raw.githubusercontent.com/a/b/main/icon.png'}
        result=c.public_app_metadata(src,'a/b')
        self.assertNotIn('screenshots',result); self.assertNotIn('unknown',result); self.assertNotIn('appPermissions',result)
        self.assertEqual(result['name'],'App')
        src['iconURL']='https://private.example/icon.png'
        with self.assertRaises(ValueError): c.public_app_metadata(src,'a/b')
