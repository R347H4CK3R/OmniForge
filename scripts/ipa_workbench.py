#!/usr/bin/env python3
"""Conservative IPA analysis for GitHub macOS runners. No automatic signing."""
import json, pathlib, plistlib, sys, zipfile, shutil, hashlib
MAX_ENTRIES=150000
MAX_TOTAL=12_000_000_000
MAX_ENTRY=2_000_000_000
ALLOWED={'.json','.plist','.strings','.stringsdict','.txt','.md','.cfg','.ini','.xml','.png','.jpg','.jpeg','.webp','.svg'}
def checked(path):
    from pathlib import PurePosixPath
    p=PurePosixPath(path)
    if not path or path.startswith('/') or '\\' in path or '..' in p.parts or '\0' in path or (p.parts and ':' in p.parts[0]):
        raise ValueError('Unsafe archive path: '+path)
    return p
def entries(z):
    info=z.infolist()
    if len(info)>MAX_ENTRIES: raise ValueError('Too many entries')
    total=0
    seen=set()
    for i in info:
        checked(i.filename)
        if i.filename in seen: raise ValueError('Duplicate path: '+i.filename)
        seen.add(i.filename)
        if i.file_size>MAX_ENTRY: raise ValueError('Oversized entry')
        total+=i.file_size
        if total>MAX_TOTAL: raise ValueError('Archive expands beyond limit')
        if (i.external_attr >> 16) & 0o170000 == 0o120000:
            raise ValueError('Symlink entry unsupported')
    return info
def inspect(src,out):
    out.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(src) as z:
        es=entries(z)
        candidates=[x for x in es if x.filename.startswith('Payload/') and x.filename.endswith('.app/Info.plist') and len(pathlib.PurePosixPath(x.filename).parts)==3]
        if not candidates: raise ValueError('No application Info.plist')
        i=candidates[0]
        if i.file_size>2_000_000: raise ValueError('Info.plist too large')
        info=plistlib.loads(z.read(i))
        summary={k:info.get(k) for k in ('CFBundleIdentifier','CFBundleName','CFBundleDisplayName','CFBundleExecutable','CFBundleVersion','CFBundleShortVersionString','MinimumOSVersion')}
        summary['entry_count']=len(es)
        summary['archive_sha256']=hashlib.sha256(src.read_bytes()).hexdigest()
        (out/'metadata.json').write_text(json.dumps(summary,indent=2,default=str))
        (out/'file_inventory.txt').write_text('\n'.join(f'{x.file_size:>12} {x.filename}' for x in es))
        (out/'README.txt').write_text('Reports describe a compiled app. Original source cannot be recovered exactly. A replaced IPA must be re-signed before installation.\n')
def unpack(src,dst):
    with zipfile.ZipFile(src) as z:
        es=entries(z)
        dst.mkdir(parents=True,exist_ok=True)
        for i in es:
            target=dst.joinpath(*checked(i.filename).parts)
            if i.is_dir(): target.mkdir(parents=True,exist_ok=True);continue
            target.parent.mkdir(parents=True,exist_ok=True)
            with z.open(i) as f, target.open('wb') as g: shutil.copyfileobj(f,g,1024*1024)
def replace(src,path,new,out):
    checked(path)
    if pathlib.PurePosixPath(path).suffix.lower() not in ALLOWED or not path.startswith('Payload/'): raise ValueError('Only nonexecutable resources supported')
    if new.stat().st_size>50_000_000: raise ValueError('Resource too large')
    with zipfile.ZipFile(src) as old:
        es=entries(old)
        if path not in [e.filename for e in es]: raise ValueError('Resource missing')
        with zipfile.ZipFile(out,'w') as fresh:
            for i in es:
                if i.filename == path: fresh.write(new,path,compress_type=zipfile.ZIP_DEFLATED)
                else:
                    with old.open(i) as stream:
                        fresh.writestr(i,stream.read())
    with zipfile.ZipFile(out) as z: assert z.testzip() is None
if __name__=='__main__':
    if sys.argv[1]=='inspect': inspect(pathlib.Path(sys.argv[2]),pathlib.Path(sys.argv[3]))
    elif sys.argv[1]=='unpack': unpack(pathlib.Path(sys.argv[2]),pathlib.Path(sys.argv[3]))
    elif sys.argv[1]=='replace': replace(pathlib.Path(sys.argv[2]),sys.argv[3],pathlib.Path(sys.argv[4]),pathlib.Path(sys.argv[5]))
    else: raise SystemExit('Unknown command')
