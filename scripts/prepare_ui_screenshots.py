#!/usr/bin/env python3
"""Safely import authorized screenshot references for clean-room UI reconstruction."""
import pathlib,sys,zipfile,json,hashlib,shutil
src=pathlib.Path(sys.argv[1]); root=pathlib.Path(sys.argv[2]);out=root/"Screenshots";out.mkdir(parents=True,exist_ok=True)
manifest=[]
with zipfile.ZipFile(src) as z:
    items=z.infolist()
    if len(items)>120:raise ValueError("Too many screenshot entries")
    for i in items:
        if i.is_dir():continue
        name=pathlib.PurePosixPath(i.filename)
        if name.is_absolute() or ".." in name.parts or "\\" in i.filename:raise ValueError("Unsafe entry")
        if name.suffix.lower() not in {".png",".jpg",".jpeg"}:continue
        if i.file_size>18_000_000:raise ValueError("Oversized screenshot")
        dest=out/("%03d_"%len(manifest)+name.name)
        with z.open(i) as f,dest.open("wb") as g:shutil.copyfileobj(f,g)
        raw=dest.read_bytes()
        if not (raw.startswith(b"\x89PNG\r\n\x1a\n") or raw.startswith(b"\xff\xd8\xff")):
            dest.unlink();raise ValueError("Unsupported image bytes")
        manifest.append({"file":dest.name,"sha256":hashlib.sha256(raw).hexdigest(),"bytes":len(raw),"screen_notes":"Record controls, navigation and states manually"})
(root/"screenshots.json").write_text(json.dumps(manifest,indent=2))
(root/"SCREEN_REBUILD_CHECKLIST.md").write_text("# Clean-room screen checklist\n\nFor each reference screenshot: identify screen name, control labels, layout sections, navigation destinations, expected interactions and accessible states. Implement original SwiftUI equivalents and compare on-device. Images alone cannot prove app functionality.\n")
print("Prepared",len(manifest),"screenshots")
