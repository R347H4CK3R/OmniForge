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
        current=dict(tag='voicematrix-v0.4.9-build11',version='0.4.9',buildVersion='11',sha256='e2d7d26ce2c7d8fa1ae92c389deead7cb0be83572bd64224b3b7a8fc91fe41d2',size=1314598007,sourceCommit='3b976fe84b6f34b2fd7668baf45533e5b7a377a5')
        self.assertEqual(e['previewApproval'],current)
        self.assertTrue(re.fullmatch(e['tagPattern'],current['tag']))
        for bad in ['voicematrix-v0.4.9-build10','voicematrix-v0.4.9-build12','voicematrix-v1.0.0-build11','voicematrix-v0x4x9-build11']:
            self.assertIsNone(re.fullmatch(e['tagPattern'],bad))
        self.assertTrue(set(self.proofs).issubset(e['requiredEvidenceAssets']))
        self.assertIn('unfinished',e['localizedDescription'].lower())
