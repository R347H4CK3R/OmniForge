#!/usr/bin/env python3
"""Single entry point for authorized IPA -> evidence -> source -> build -> acceptance.

A successful scaffold build is NOT equivalent to recovery of the source or behavior.
Must run on a Mac with Xcode for compilation. Optional agent needs local Ollama.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from server.autonomous_reconstruction import reconstruct
from server.behavior_gate import assess

def command(argv, timeout=180):
    result=subprocess.run([sys.executable,*argv],cwd=ROOT,text=True,
                          capture_output=True,timeout=timeout,shell=False)
    if result.returncode:
        raise RuntimeError(("Step failed: "+Path(argv[0]).name+"\n"+result.stderr[-2500:])[:3000])
    return result.stdout[-1000:]

def execute(ipa, destination, evidence=None, agent=None, compiler=None):
    ipa=Path(ipa).resolve()
    dest=Path(destination).resolve()
    if not ipa.is_file() or ipa.suffix.lower()!=".ipa":
        raise ValueError("An existing .ipa is required")
    if dest==ipa or dest in ipa.parents:
        raise ValueError("Invalid output path")
    dest.mkdir(parents=True,exist_ok=True)
    project=dest/"project"
    analysis=dest/"evidence"
    digest=hashlib.sha256()
    with ipa.open("rb") as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b""):
            digest.update(chunk)
    report={"schema":1,"source_ipa_sha256":digest.hexdigest(),
            "started":datetime.now(timezone.utc).isoformat(),"stages":{},
            "complete":False,"functional_equivalence_verified":False}
    def save():
        (dest/"reconstruction-status.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    try:
        command(["scripts/generate_scaffold.py",str(ipa),str(project)])
        report["stages"]["project_generation"]="PASS"
        # Prepare architecture and resource inventory from the same IPA automatically.
        command(["scripts/prepare_ghidra_ipa.py",str(ipa),str(analysis)])
        report["stages"]["binary_inventory"]="PASS"
        if evidence:
            source=Path(evidence).resolve()
            if not source.is_dir(): raise ValueError("Evidence directory missing")
            command(["scripts/enhance_reconstruction.py",str(project),str(source)])
            analysis=source
            report["stages"]["evidence_import"]="PASS"
        else:
            report["stages"]["evidence_import"]="BINARY_INVENTORY_ONLY"
            command(["scripts/enhance_reconstruction.py",str(project),str(analysis)])
        if agent is None:
            report["stages"]["autonomous_source_implementation"]="NOT_CONFIGURED"
            # Compilation alone never proves functional behavior.
            from server.autonomous_reconstruction import verify_xcode_project
            result=(compiler or verify_xcode_project)(project)
            report["stages"]["compilation"]=result
        else:
            result=reconstruct(project,analysis,agent,verify=compiler or
                __import__("server.autonomous_reconstruction",fromlist=["verify_xcode_project"]).verify_xcode_project)
            report["stages"]["autonomous_source_implementation"]=result
            report["stages"]["compilation"]={"passed":result["compiled"]}
        behavior=assess(project,analysis)
        report["stages"]["behavioral_acceptance"]=behavior
        built=bool(report["stages"]["compilation"].get("passed"))
        report["functional_equivalence_verified"]=built and behavior["passed"]
        report["complete"]=report["functional_equivalence_verified"] and agent is not None
    except Exception as error:
        report["error"]=str(error)[:3000]
    finally:
        save()
    return report

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("ipa");p.add_argument("output")
    p.add_argument("--evidence",help="Ghidra exports and independent acceptance.json")
    p.add_argument("--local-agent",action="store_true",help="Use configured local OmniForge Ollama agent")
    args=p.parse_args()
    agent=None
    if args.local_agent:
        from server.agent_server import agent as chat, MODEL, ROOT as workspace
        target=(Path(args.output).resolve()/"project")
        if workspace!=target and workspace not in target.parents:
            p.error("Set OMNIFORGE_WORKSPACE to a parent of the output project")
        agent=lambda text:chat([{"role":"user","content":text}],MODEL)
    result=execute(args.ipa,args.output,args.evidence,agent=agent)
    print(json.dumps(result,indent=2))
    return 0 if result["complete"] else 1

if __name__=="__main__": raise SystemExit(main())
