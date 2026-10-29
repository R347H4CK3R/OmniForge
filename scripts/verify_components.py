#!/usr/bin/env python3
"""Machine-readable OmniForge verification gate.

Independent system/device tests are NEVER inferred from a successful compiler job.
Supply attested evidence JSON to count any end-to-end component as verified.
"""
import argparse
import json
import pathlib
import sys
from datetime import datetime, timezone

COMPONENTS = {
 "python_agent_tests": "ci",
 "windows_host_packaging": "ci",
 "ios_app_compilation": "ci",
 "ghidra_analysis": "ci",
 "ipa_attachment_on_device": "device",
 "real_ipa_decompilation": "system",
 "source_reconstruction": "system",
 "ios_rebuild": "system",
 "behavioral_equivalence": "device",
 "iphone_controls_windows": "device",
 "wifi_and_cellular_remote": "device",
 "livecontainer_iphone_launch": "device",
}
VALID={"PASS","FAIL","BLOCKED","NOT_TESTED"}
def evaluate(evidence):
    entries=evidence.get("checks",{}) if isinstance(evidence,dict) else {}
    if not isinstance(entries,dict):
        raise ValueError("checks must be an object")
    rows=[]
    for component,kind in COMPONENTS.items():
        item=entries.get(component,{})
        if not isinstance(item,dict):
            item={}
        status=item.get("status","NOT_TESTED")
        if status not in VALID:
            status="NOT_TESTED"
        run=item.get("run_url","")
        sha=item.get("commit_sha","")
        device=item.get("device_id","")
        if status=="PASS" and (not isinstance(run,str) or not run.startswith("https://") or
                              not isinstance(sha,str) or len(sha)<7 or
                              (kind=="device" and (not isinstance(device,str) or not device.strip()))):
            status="NOT_TESTED"
        rows.append({"component":component,"kind":kind,"status":status,
                     "run_url":run if isinstance(run,str) else "",
                     "commit_sha":sha if isinstance(sha,str) else ""})
    return {"schema":1,"generated_at":datetime.now(timezone.utc).isoformat(),
            "complete":all(x["status"]=="PASS" for x in rows),
            "checks":rows}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--evidence",type=pathlib.Path)
    parser.add_argument("--output",type=pathlib.Path,default=pathlib.Path("verification-report.json"))
    parser.add_argument("--require-complete",action="store_true")
    args=parser.parse_args()
    source=json.loads(args.evidence.read_text()) if args.evidence else {}
    result=evaluate(source)
    args.output.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps({"complete":result["complete"],"passed":sum(x["status"]=="PASS" for x in result["checks"]),
                      "total":len(result["checks"])}))
    return 1 if args.require_complete and not result["complete"] else 0
if __name__=="__main__":
    sys.exit(main())
