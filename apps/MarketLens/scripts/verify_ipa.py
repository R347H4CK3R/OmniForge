"""Validate native package identity and write reproducible release evidence."""
import hashlib,json,os,plistlib,struct,sys,zipfile
from pathlib import Path,PurePosixPath

def verify(path):
 path=Path(path)
 with zipfile.ZipFile(path) as z:
  names=z.namelist()
  if any(n.startswith('/') or '..' in PurePosixPath(n).parts for n in names):raise ValueError('Unsafe archive path')
  infos=[n for n in names if n.startswith('Payload/') and n.count('/')==2 and n.endswith('.app/Info.plist')]
  if len(infos)!=1:raise ValueError('Expected exactly one native app payload')
  info=plistlib.loads(z.read(infos[0]))
  expected={'CFBundleIdentifier':'com.r347h4ck3r.marketlens','CFBundleShortVersionString':'0.1.0','CFBundleVersion':'1','MinimumOSVersion':'26.0'}
  for key,value in expected.items():
   if info.get(key)!=value:raise ValueError(f'{key} mismatch: {info.get(key)!r}')
  executable=info.get('CFBundleExecutable','')
  if not executable or '/' in executable:raise ValueError('Invalid executable')
  body=z.read(str(PurePosixPath(infos[0]).parent/executable))
  if len(body)<32 or struct.unpack('<II',body[:8])!=(0xfeedfacf,0x0100000c):raise ValueError('Expected thin ARM64 Mach-O executable')
 return {'filename':path.name,'bundleIdentifier':info['CFBundleIdentifier'],'version':info['CFBundleShortVersionString'],'buildVersion':info['CFBundleVersion'],'minOSVersion':info['MinimumOSVersion'],'size':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'architecture':'arm64','signed':False,'sourceCommit':os.environ.get('GITHUB_SHA'),'workflowRun':os.environ.get('GITHUB_RUN_ID'),'physicalDeviceVerified':False,'forecastValidated':False}
if __name__=='__main__':
 result=verify(sys.argv[1]); print(json.dumps(result,indent=2))
