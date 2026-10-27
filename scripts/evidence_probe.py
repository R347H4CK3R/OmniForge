#!/usr/bin/env python3
"""Bounded evidence-driven IPA inspection. No code execution, decryption or proprietary extraction."""
import sys,json,zipfile,struct,re,hashlib,pathlib
def examine(path):
  result={"input":pathlib.Path(path).name,"archives":[],"hypotheses":[],"next_checks":[]}
  with zipfile.ZipFile(path) as z:
    items=z.infolist()
    if len(items)>150000:raise ValueError("Too many ZIP entries")
    for entry in items:
      if entry.is_dir():continue
      if not entry.filename.lower().endswith(".dz"):continue
      with z.open(entry) as stream:prefix=stream.read(min(131072,entry.file_size))
      item={"name":entry.filename,"size":entry.file_size,"prefix_sha256":hashlib.sha256(prefix).hexdigest(),
            "header":prefix[:32].hex(),"detected":"DTRZ" if prefix.startswith(b"DTRZ") else "unknown",
            "filename_evidence":[],"claims":[]}
      if prefix.startswith(b"DTRZ") and len(prefix)>=9:
        count=struct.unpack_from("<H",prefix,4)[0]
        item["candidate_count_field"]=count
        matches=re.finditer(rb"[\x20-\x7e]{5,160}\x00",prefix)
        for m in matches:
          name=m.group()[:-1].decode("ascii","replace")
          if "." in name or "/" in name:
            item["filename_evidence"].append({"offset":m.start(),"value":name})
          if len(item["filename_evidence"])>=300:break
        item["claims"].append({"hypothesis":"header u16 at offset 4 may represent file count",
             "support":"compare with names found in prefix","confirmed":False})
      result["archives"].append(item)
  result["next_checks"]=["Inspect directory offset/table bounds before attempting extraction.",
    "Compare candidate counts across independent archives.",
    "Identify payload compression independently; do not assume ZIP.",
    "If encrypted or DRM-protected, report limitation without asserting decryption."]
  return result
if __name__=="__main__":
  if len(sys.argv)!=3:raise SystemExit("Usage: evidence_probe.py input.ipa output.json")
  pathlib.Path(sys.argv[2]).write_text(json.dumps(examine(sys.argv[1]),indent=2))
