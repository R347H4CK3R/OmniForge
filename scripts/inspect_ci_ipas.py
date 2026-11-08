#!/usr/bin/env python3
"""Read-only inspection of public CI artifacts; never executes or publishes IPAs."""
import argparse
import hashlib
import json
import plistlib
import zipfile
from pathlib import Path
from unified_catalog import inspect_ipa, MAX_IPA


def inspect_directory(directory):
    candidates=sorted(directory.rglob('*.ipa'))
    if not candidates or len(candidates)>20: raise ValueError('expected 1–20 IPA files')
    result=[]
    for path in candidates:
        if path.is_symlink() or not path.is_file() or not 0<path.stat().st_size<=MAX_IPA:
            raise ValueError('invalid IPA file')
        if directory.resolve() not in path.resolve().parents: raise ValueError('IPA escapes artifact directory')
        with zipfile.ZipFile(path) as z:
            names=[n for n in z.namelist() if n.startswith('Payload/') and n.count('/')==2 and n.endswith('.app/Info.plist')]
            if len(names)!=1 or z.getinfo(names[0]).file_size>1_000_000: raise ValueError('invalid app metadata')
            info=plistlib.loads(z.read(names[0]));bid=info['CFBundleIdentifier']
        details=inspect_ipa(path,bid)
        digest=hashlib.sha256()
        with path.open('rb') as stream:
            for chunk in iter(lambda:stream.read(1024*1024),b''):digest.update(chunk)
        result.append({'file':path.name,'bundleIdentifier':bid,'size':path.stat().st_size,'sha256':digest.hexdigest(),**details})
    return result


def main():
    p=argparse.ArgumentParser();p.add_argument('directory',type=Path);p.add_argument('--output',type=Path,default=Path('ipa-inspection.json'));args=p.parse_args()
    result={'status':'structure-verified-only','apps':inspect_directory(args.directory),
            'limits':'No app executed. No gameplay, physical-device, signing, content-rights or secret-content certification. No binaries published.'}
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
