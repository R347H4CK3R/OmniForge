#!/usr/bin/env python3
"""Select main executable from a user-authorized IPA and create screenshot evidence index."""
import pathlib,sys,zipfile,plistlib,json,shutil
ipa=pathlib.Path(sys.argv[1]); dest=pathlib.Path(sys.argv[2]);dest.mkdir(parents=True,exist_ok=True)
with zipfile.ZipFile(ipa) as z:
    infos=z.infolist()
    if len(infos)>100000:raise ValueError("Too many entries")
    plists=[i for i in infos if i.filename.startswith("Payload/") and i.filename.endswith(".app/Info.plist") and len(pathlib.PurePosixPath(i.filename).parts)==3]
    if len(plists)!=1:raise ValueError("Expected exactly one main app")
    p=plists[0]; metadata=plistlib.loads(z.read(p))
    name=metadata.get("CFBundleExecutable")
    if not name or '/' in name:raise ValueError("Unsafe executable name")
    binary=p.filename.removesuffix("Info.plist")+name
    member=z.getinfo(binary)
    if member.file_size>500_000_000:raise ValueError("Executable too large")
    with z.open(member) as src,(dest/"main_macho").open("wb") as target:shutil.copyfileobj(src,target,1024*1024)
    assets=[{"path":i.filename,"bytes":i.file_size} for i in infos if i.filename.lower().endswith((".storyboardc",".nib",".png",".jpg",".jpeg",".car",".strings",".stringsdict"))][:3000]
    (dest/"interface_evidence.json").write_text(json.dumps({"bundle_id":metadata.get("CFBundleIdentifier"),"original_executable":binary,"resources":assets},indent=2))
    (dest/"UI_REBUILD_GUIDE.md").write_text("# Screen reconstruction workspace\n\nReference screenshots should be added only when you have rights to use them. The screenshots and resource inventory are evidence; they cannot directly recover the original view code.\n\n1. Review screenshot files in Screenshots/ and interface_evidence.json.\n2. Record screen titles, controls, spacing, state changes and navigation.\n3. Reimplement screens with original SwiftUI views and permitted assets.\n4. Compare screenshots to rebuilt app during actual device tests.\n")
print(binary)
