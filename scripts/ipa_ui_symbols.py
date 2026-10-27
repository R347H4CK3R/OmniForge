#!/usr/bin/env python3
"""Evidence-driven UI and symbol inventory for authorized, unpacked IPAs."""
import pathlib, json, re, sys, subprocess, plistlib, hashlib
root=pathlib.Path(sys.argv[1]).resolve(); out=pathlib.Path(sys.argv[2]); out.mkdir(parents=True,exist_ok=True)
if not (root/"Payload").is_dir(): raise SystemExit("Expected unpacked Payload")
ui_ext={".nib",".storyboard",".strings",".stringsdict",".car",".png",".jpg",".jpeg",".webp",".pdf",".plist"}
ui=[]; binary=[]
for path in root.rglob("*"):
    if not path.is_file() or path.is_symlink(): continue
    rel=path.relative_to(root).as_posix()
    if path.suffix.lower() in ui_ext and len(ui)<15000:
        ui.append({"path":rel,"size":path.stat().st_size,"type":path.suffix.lower()})
    if path.stat().st_size<400_000_000 and len(binary)<100:
        result=subprocess.run(["file","-b",str(path)],capture_output=True,text=True).stdout
        if "Mach-O" in result: binary.append(path)
(out/"ui_inventory.json").write_text(json.dumps(ui,indent=2))
reports=[]
for p in binary:
    rel=p.relative_to(root).as_posix()
    item={"path":rel,"symbols":[],"objc_and_swift_strings":[],"linked_libraries":[]}
    def run(*args):
        try:return subprocess.run(args,capture_output=True,text=True,timeout=35).stdout[:1500000]
        except Exception:return ""
    symbols=run("nm","-g",str(p)).splitlines()
    item["symbols"]=symbols[:2500]
    item["linked_libraries"]=run("otool","-L",str(p)).splitlines()[:120]
    strings=run("strings","-a",str(p)).splitlines()
    pattern=re.compile(r"(OBJC_CLASS_\$_|OBJC_METACLASS_\$_|\$s[A-Za-z0-9_]{7,}|UIViewController|UIStoryboard|NSClassFromString|swift|objc|ViewController|\.nib|\.storyboard)",re.I)
    item["objc_and_swift_strings"]=[v[:320] for v in strings if pattern.search(v)][:3500]
    reports.append(item)
(out/"class_method_evidence.json").write_text(json.dumps(reports,indent=2))
(out/"UI_RECONSTRUCTION.md").write_text("""# UI reconstruction evidence

This directory inventories original packaged UI resources and observable symbol names.
Storyboard/nib/.car files are compiled resources, not their editable original projects.
No screenshots or navigation flows can be inferred reliably from filenames alone.

## Recommended approach
1. Inspect ui_inventory.json for asset/storyboard/localization evidence.
2. Extract only assets you have rights to reuse.
3. Rebuild a new SwiftUI interface manually from authorized screenshots and actual user flows.
4. Compile and test the clean-room scaffold separately.
5. Do not label inferred code or screens as recovered originals.

Binary class/method strings and symbols are clues, not validated declarations or source recovery.
""")
print(json.dumps({"ui_resources":len(ui),"mach_o_files":len(binary)}))
