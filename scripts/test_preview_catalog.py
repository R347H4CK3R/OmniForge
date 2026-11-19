import copy,json,re,unittest
from pathlib import Path
import unified_catalog as c

class PreviewEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.pin=dict(tag='voicematrix-v0.4.9-build10',version='0.4.9',buildVersion='10',sha256='8adee1c45510ac22557b77ed0bbb7d32346cbc39a11efaf9bcea16f9e43622fd',size=1314595724,sourceCommit='e7023843438a2ed82ef95a7ee96df12ea56d68e9')
        self.entry={'bundleIdentifier':'com.voicematrix.app','previewApproval':self.pin}
        self.actual={'version':'0.4.9','buildVersion':'10'}
        self.proofs={
          'release-metadata.json':dict(self.pin,unfinishedPreview=True,physicalDeviceVerified=False,likenessVerified=False),
          'character-inspection.json':dict(archive='passed',bundleIdentifier='com.voicematrix.app',version='0.4.9',build='10',physicalIPhoneVerified=False,characterLikenessVerified=False),
          'packaging-status.json':dict(sourceCommit=self.pin['sourceCommit'],version='0.4.9',build='10',nativeTestsRun=False,hostExtractionTestsPassed=True,physicalDeviceVerified=False,likenessVerified=False),
          'source-proof.json':dict(sourceCommit=self.pin['sourceCommit'])}
    def check(self):
        c.verify_packaging_preview(self.entry,self.pin['tag'],self.proofs,self.actual,self.pin['sha256'],self.pin['size'])
    def test_verifier_exists(self):
        self.assertTrue(callable(getattr(c,'verify_packaging_preview',None)))
    def test_exact_unfinished_preview_passes(self): self.check()
    def test_missing_proof_rejected(self):
        for name in list(self.proofs):
            with self.subTest(name=name):
                saved=self.proofs.pop(name)
                with self.assertRaises(ValueError):self.check()
                self.proofs[name]=saved
    def test_changed_identity_or_completion_claim_rejected(self):
        mutations=[('release-metadata.json','sha256','0'*64),('release-metadata.json','size',1),('release-metadata.json','unfinishedPreview',False),('release-metadata.json','physicalDeviceVerified',True),('release-metadata.json','likenessVerified',True),('release-metadata.json','sourceCommit','0'*40),('character-inspection.json','bundleIdentifier','wrong'),('character-inspection.json','archive','failed'),('character-inspection.json','build','11'),('character-inspection.json','characterLikenessVerified',True),('packaging-status.json','nativeTestsRun',True),('packaging-status.json','hostExtractionTestsPassed',False),('packaging-status.json','sourceCommit','0'*40),('source-proof.json','sourceCommit','0'*40)]
        for name,key,value in mutations:
            with self.subTest(name=name,key=key):
                old=self.proofs[name][key];self.proofs[name][key]=value
                with self.assertRaises(ValueError):self.check()
                self.proofs[name][key]=old
    def test_other_tag_ipa_or_invalid_pin_rejected(self):
        for tag,sha,size,actual in [('voicematrix-v0.4.9-build11',self.pin['sha256'],self.pin['size'],self.actual),(self.pin['tag'],'0'*64,self.pin['size'],self.actual),(self.pin['tag'],self.pin['sha256'],1,self.actual),(self.pin['tag'],self.pin['sha256'],self.pin['size'],dict(version='1.0.0',buildVersion='10'))]:
            with self.assertRaises(ValueError): c.verify_packaging_preview(self.entry,tag,self.proofs,actual,sha,size)
        self.entry.pop('previewApproval')
        with self.assertRaises(ValueError):self.check()
    def test_character_gate_not_satisfied_by_packaging_evidence(self):
        with self.assertRaises(ValueError):c.verify_character_evidence(self.proofs['character-inspection.json'],'com.voicematrix.app',self.actual,self.pin['sha256'],self.pin['size'])
    def test_registry_is_exact_build_preview_with_all_evidence(self):
        registry=json.loads((Path(__file__).resolve().parents[1]/'catalog/registry.json').read_text())
        e=next(x for x in registry if x['bundleIdentifier']=='com.voicematrix.app')
        self.assertEqual(e['evidencePolicy'],'packaging-preview-v1')
        current=dict(tag='voicematrix-v0.4.15-build18',version='0.4.15',buildVersion='18',sha256='0ca301717b02b9e10976aaa141a3e1642667f8d1fd5d7d6e1a2a99fd35cb4038',size=1330532529,sourceCommit='5c0d71108a751c18a434d7b40e6357ce215d582e')
        self.assertEqual(e['previewApproval'],current)
        self.assertTrue(re.fullmatch(e['tagPattern'],current['tag']))
        for bad in ['voicematrix-v0.4.13-build16','voicematrix-v0.4.9-build12','voicematrix-v0.4.10-build13','voicematrix-v1.0.0-build14','voicematrix-v0x4x11-build14']:
            self.assertIsNone(re.fullmatch(e['tagPattern'],bad))
        self.assertTrue(set(self.proofs).issubset(e['requiredEvidenceAssets']))
        self.assertNotIn('sourceURL',e)
        self.assertEqual(e['assetPattern'],re.escape('VoiceMatrix-0.4.15-build18.ipa'))
        self.assertIn('free noncommercial voicematrix preview',e['localizedDescription'].lower())
        self.assertIn('remain unverified',e['localizedDescription'].lower())

    def test_failed_refresh_retains_current_verified_orivyn(self):
        root=Path(__file__).resolve().parents[1]
        state=json.loads((root/'catalog/verified-state.json').read_text())
        registry=json.loads((root/'catalog/registry.json').read_text())
        def unavailable(_):raise ValueError('synthetic unavailable release')
        result,errors=c.refresh(state,registry,loader=unavailable)
        self.assertEqual(result['apps'],state['apps'])
        app=next(a for a in result['apps'] if a['bundleIdentifier']=='app.jarvisevo.ios')
        original=next(a for a in state['apps'] if a['bundleIdentifier']=='app.jarvisevo.ios')
        self.assertEqual(app,original)
        self.assertTrue(app['_verification']['sha256'])
        self.assertEqual(app['downloadURL'],app['versions'][0]['downloadURL'])
