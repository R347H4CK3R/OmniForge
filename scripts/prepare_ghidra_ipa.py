#!/usr/bin/env python3
"""Prepare an authorized IPA for Ghidra, including universal ARMv7/ARM64 binaries."""
import pathlib, sys, zipfile, plistlib, json, struct, shutil, hashlib
src=pathlib.Path(sys.argv[1]); out=pathlib.Path(sys.argv[2]); out.mkdir(parents=True,exist_ok=True)
with zipfile.ZipFile(src) as z:
    files=z.infolist()
    if len(files)>100000: raise ValueError("Too many IPA entries")
    plists=[i for i in files if i.filename.startswith("Payload/") and i.filename.endswith(".app/Info.plist") and len(pathlib.PurePosixPath(i.filename).parts)==3]
    if len(plists)!=1:raise ValueError("Exactly one main app expected")
    if plists[0].file_size>2000000: raise ValueError("Oversized Info.plist")
    info=plistlib.loads(z.read(plists[0]))
    exe=info["CFBundleExecutable"]
    if not isinstance(exe,str) or "/" in exe or "\\" in exe:raise ValueError("Invalid executable")
    binary=plists[0].filename[:-len("Info.plist")]+exe
    entry=z.getinfo(binary)
    if entry.file_size>600000000:raise ValueError("Executable too large")
    with z.open(entry) as stream,(out/"main_macho").open("wb") as target:shutil.copyfileobj(stream,target,1024*1024)
    resources=[{"name":e.filename,"bytes":e.file_size,"kind":"DTRZ game archive" if e.filename.lower().endswith(".dz") else "resource"} for e in files if e.filename.lower().endswith((".dz",".car",".nib",".storyboardc",".png",".jpg",".plist"))][:3000]
blob=(out/"main_macho").read_bytes()
slices=[]
if blob[:4] in (bytes.fromhex("cafebabe"),bytes.fromhex("bebafeca")):
    fmt=">" if blob[:4]==bytes.fromhex("cafebabe") else "<"
    count=struct.unpack_from(fmt+"I",blob,4)[0]
    if not 1<=count<=20:raise ValueError("Invalid architecture count")
    for i in range(count):
        cpu,sub,offset,size,align=struct.unpack_from(fmt+"IIIII",blob,8+i*20)
        if offset+size>len(blob) or size<32:raise ValueError("Invalid architecture bounds")
        label="arm64" if cpu==0x0100000c else "armv7" if cpu==12 else "cpu_"+hex(cpu)[2:]
        filename="main_"+label+".macho"
        (out/filename).write_bytes(blob[offset:offset+size])
        slices.append({"name":label,"file":filename,"size":size,"cpu":cpu,"sha256":hashlib.sha256(blob[offset:offset+size]).hexdigest()})
else:
    slices=[{"name":"single","file":"main_macho","size":len(blob)}]
(out/"architectures.json").write_text(json.dumps({"app_id":info.get("CFBundleIdentifier"),"slices":slices,"resources":resources},indent=2))
(out/"UI_REBUILD_GUIDE.md").write_text("# Reconstruction evidence\n\nThe IPA contains compiled binaries and packaged resources, not original project source. For mixed architecture apps, analyze each executable slice separately. Proprietary DTRZ archives must be studied independently without assuming ZIP compression.\n")
print(json.dumps(slices))
