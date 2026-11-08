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

    def test_embedded_library_raises_effective_minimum_ios(self):
        import struct
        with tempfile.TemporaryDirectory() as d:
            p=self.archive(d)
            with zipfile.ZipFile(p,'a') as z:
                z.writestr('Payload/Example.app/Frameworks/Helper.dylib',struct.pack('<8I',0xfeedfacf,0x100000c,0,6,1,24,0,0)+struct.pack('<6I',0x32,24,2,18<<16,0,0))
            self.assertEqual(self.c.inspect_ipa(p,'com.example.app')['minOSVersion'],'18.0')

    def test_rejects_embedded_simulator_library(self):
        import struct
        with tempfile.TemporaryDirectory() as d:
            p=self.archive(d)
            with zipfile.ZipFile(p,'a') as z:
                z.writestr('Payload/Example.app/Frameworks/Helper.dylib',struct.pack('<8I',0xfeedfacf,0x100000c,0,6,1,24,0,0)+struct.pack('<6I',0x32,24,7,17<<16,0,0))
            with self.assertRaises(ValueError):self.c.inspect_ipa(p,'com.example.app')

    def test_privacy_is_read_from_actual_ipa_not_source_metadata(self):
        with tempfile.TemporaryDirectory() as d:
            p=self.archive(d,NSMicrophoneUsageDescription='Record only when requested',PrivateOtherField='not exposed')
            details=self.c.inspect_ipa(p,'com.example.app',include_permissions=True)
            self.assertEqual(details['appPermissions']['privacy'],{'NSMicrophoneUsageDescription':'Record only when requested'})
            self.assertNotIn('PrivateOtherField',str(details))

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

class ReleaseSelectionTests(unittest.TestCase):
    def setUp(self):
        import unified_catalog
        self.c=unified_catalog
        self.entry={'repository':'a/b','tagPattern':'v[0-9]+','assetPattern':'App\\.ipa','allowPrerelease':False}
        self.release={'tag_name':'v1','draft':False,'prerelease':False,'published_at':'2026-01-01T00:00:00Z',
                      'assets':[{'name':'App.ipa','state':'uploaded','size':20,'browser_download_url':'https://github.com/a/b/releases/download/v1/App.ipa'}]}

    def test_selects_newest_approved_ipa_not_unrelated_or_draft(self):
        newer=copy.deepcopy(self.release);newer.update(tag_name='v2',published_at='2026-02-01T00:00:00Z')
        newer['assets'][0]['browser_download_url']='https://github.com/a/b/releases/download/v2/App.ipa'
        unrelated=dict(newer,tag_name='windows-3',published_at='2026-03-01T00:00:00Z')
        draft=dict(newer,draft=True,published_at='2026-04-01T00:00:00Z')
        release,asset=self.c.select_public_release([unrelated,self.release,draft,newer],self.entry)
        self.assertEqual(release['tag_name'],'v2');self.assertEqual(asset['name'],'App.ipa')

    def test_does_not_silently_promote_prerelease(self):
        with self.assertRaises(ValueError): self.c.select_public_release([dict(self.release,prerelease=True)],self.entry)

    def test_rejects_ambiguous_multiple_ipa_assets(self):
        release=copy.deepcopy(self.release);release['assets'].append(dict(release['assets'][0]))
        with self.assertRaises(ValueError): self.c.select_public_release([release],self.entry)

    def test_requires_uploaded_positive_size_assets(self):
        for change in ({'state':'new'},{'size':0}):
            release=copy.deepcopy(self.release);release['assets'][0].update(change)
            with self.assertRaises(ValueError): self.c.select_public_release([release],self.entry)

class CatalogIconTests(unittest.TestCase):
    def test_owner_avatar_allowed_only_for_correct_repository_owner(self):
        import unified_catalog as c
        src={'name':'Prototype','bundleIdentifier':'a','iconURL':'https://github.com/owner.png'}
        self.assertEqual(c.public_app_metadata(src,'owner/repo')['iconURL'],src['iconURL'])
        with self.assertRaises(ValueError):c.public_app_metadata(src,'different/repo')

class StoreGuideTests(unittest.TestCase):
    def test_guide_uses_live_catalog_and_escapes_text(self):
        import unified_catalog as c
        app={'name':'App <unsafe>','bundleIdentifier':'a','localizedDescription':'Prototype & test','iconURL':'https://github.com/owner.png',
             'versions':[{'version':'1.2','buildVersion':'3','minOSVersion':'17.0','size':1200000,'downloadURL':'https://github.com/a/b/releases/download/v1/a.ipa','localizedDescription':'Changes <safe>'}]}
        guide=c.render_store_guide({'apps':[app]})
        self.assertIn('App &lt;unsafe&gt;',guide);self.assertIn('1.2',guide);self.assertIn('17.0',guide)
        self.assertNotIn('App <unsafe>',guide);self.assertIn('Physical-device',guide)
