#!/usr/bin/env python3
"""Decide and prepare an honest, supported IPA modification path."""
import json, pathlib, sys, zipfile, plistlib, subprocess
ipa=pathlib.Path(sys.argv[1]); out=pathlib.Path(sys.argv[2]); out.mkdir(parents=True,exist_ok=True)
with zipfile.ZipFile(ipa) as z:
    infos=z.infolist()
    p=[i for i in infos if i.filename.startswith("Payload/") and i.filename.endswith(".app/Info.plist") and len(pathlib.PurePosixPath(i.filename).parts)==3]
    if len(p)!=1: raise ValueError("IPA must contain exactly one primary app")
    info=plistlib.loads(z.read(p[0]))
    resources=[i.filename for i in infos if i.filename.lower().endswith((".json",".plist",".strings",".txt",".cfg",".ini",".png",".jpg",".jpeg",".xml"))]
    compiled=[i.filename for i in infos if ".app/" in i.filename and not i.is_dir()]
    report={
      "app":info.get("CFBundleIdentifier","unknown"),
      "source_present":False,
      "compilable_reconstruction":"clean_room_only",
      "resource_patch_supported":bool(resources),
      "resource_candidates":resources[:100],
      "original_binary_editable_as_source":False,
      "steps":[
         "Search authorized source repositories manually or by configured provider.",
         "Build independent clean-room SwiftUI project using documented behavior.",
         "For supported non-executable changes use resource replacement and re-sign.",
         "Do not assume generated code reproduces original binary behavior."
      ]}
    (out/"decision.json").write_text(json.dumps(report,indent=2))
    print(json.dumps({"app":report["app"],"resource_candidates":len(resources)}))
