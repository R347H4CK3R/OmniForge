import unittest,tempfile,zipfile,plistlib,struct
from pathlib import Path
from verify_ipa import verify
class VerifyTests(unittest.TestCase):
 def fixture(self,path,bundle='com.r347h4ck3r.marketlens',cpu=0x0100000c):
  with zipfile.ZipFile(path,'w') as z:
   z.writestr('Payload/MarketLens.app/Info.plist',plistlib.dumps(dict(CFBundleIdentifier=bundle,CFBundleShortVersionString='0.1.0',CFBundleVersion='1',MinimumOSVersion='26.0',CFBundleExecutable='MarketLens')))
   z.writestr('Payload/MarketLens.app/MarketLens',struct.pack('<IIIIIIII',0xfeedfacf,cpu,0,2,0,0,0,0))
 def test_valid_metadata_and_hash(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'MarketLens.ipa';self.fixture(p);result=verify(p)
   self.assertEqual(result['bundleIdentifier'],'com.r347h4ck3r.marketlens');self.assertEqual(result['size'],p.stat().st_size);self.assertEqual(len(result['sha256']),64)
 def test_wrong_identity_and_architecture_fail(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'bad.ipa'
   self.fixture(p,bundle='another.app')
   with self.assertRaises(ValueError):verify(p)
   self.fixture(p,cpu=0x01000007)
   with self.assertRaises(ValueError):verify(p)
 def test_missing_payload_fails(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'bad.ipa'
   with zipfile.ZipFile(p,'w') as z:z.writestr('oops','wrong')
   with self.assertRaises(ValueError):verify(p)
if __name__=='__main__':unittest.main()
