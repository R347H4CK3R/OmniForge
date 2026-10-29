"""Explicit functional acceptance gate for reconstructed application builds.

Evidence manifests contain externally observed, independently verified requirements.
A compiled scaffold cannot pass this gate without supplied machine-readable
test results for every required behavior.
"""
import json
from pathlib import Path

def assess(project, evidence):
    project=Path(project)
    evidence=Path(evidence)
    manifest=evidence/"acceptance.json"
    results=project/"acceptance-results.json"
    if not manifest.is_file():
        return {"passed":False,"status":"UNVERIFIED","reason":"No independently specified behavioral acceptance manifest"}
    try:
        spec=json.loads(manifest.read_text(encoding="utf-8"))
        required=spec["requirements"]
        if not isinstance(required,list) or not required or len(required)>300:
            raise ValueError("Expected 1-300 requirements")
        ids=[item["id"] for item in required]
        if any(not isinstance(x,str) or not x or len(x)>120 for x in ids) or len(set(ids))!=len(ids):
            raise ValueError("Invalid or duplicate requirement IDs")
        if not results.is_file():
            return {"passed":False,"status":"UNVERIFIED","reason":"No executed behavior test report"}
        data=json.loads(results.read_text(encoding="utf-8"))
        cases=data["cases"]
        if not isinstance(cases,list) or len(cases)>300: raise ValueError("Invalid cases")
        by_id={c["id"]:c for c in cases}
        if len(by_id)!=len(cases): raise ValueError("Duplicate case IDs")
        failed=[id for id in ids if by_id.get(id,{}).get("status")!="PASS" or
                not by_id.get(id,{}).get("evidence")]
        return {"passed":not failed,"status":"PASS" if not failed else "FAIL",
                "required":len(ids),"failed":failed}
    except (ValueError,TypeError,KeyError,json.JSONDecodeError) as e:
        return {"passed":False,"status":"INVALID","reason":str(e)[:400]}
