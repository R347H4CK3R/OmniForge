#!/usr/bin/env python3
"""One-command end-to-end readiness audit; never fabricates a device test.

Runs actual local checks, validates inputs, and emits JSON plus readable Markdown.
CI, signing and live iPhone actions require externally supplied evidence.
"""
import argparse
import json
import pathlib
import socket
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone

def check_tcp(host,port,hello=False):
    try:
        with socket.create_connection((host,port),timeout=4) as s:
            s.settimeout(4)
            banner=s.recv(12) if hello else b""
        if hello and not banner.startswith(b"RFB "):
            return "FAIL","Unexpected VNC protocol banner"
        return "PASS",("RFB banner: "+banner.decode("ascii","replace").strip()) if hello else "TCP connected"
    except OSError as e:
        return "FAIL",str(e)[:250]

def check_http(url):
    try:
        with urllib.request.urlopen(url,timeout=5) as response:
            return ("PASS" if response.status==200 else "FAIL"),"HTTP "+str(response.status)
    except Exception as e:
        return "FAIL",str(e)[:250]

def check_command(args,root,seconds=120):
    try:
        p=subprocess.run(args,cwd=str(root),shell=False,stdin=subprocess.DEVNULL,
                         stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=seconds)
        return ("PASS" if p.returncode==0 else "FAIL"),("exit="+str(p.returncode)+" "+(p.stderr or p.stdout)[-300:])
    except (OSError,subprocess.TimeoutExpired) as e:
        return "FAIL",str(e)[:250]

def audit(root):
    result=[]
    def record(name,kind,fn=None):
        if fn is None:
            status,detail="NOT_TESTED","Requires separate evidence or a real device"
        else:
            try: status,detail=fn()
            except Exception as e: status,detail="FAIL",str(e)[:250]
        result.append({"name":name,"category":kind,"status":status,"detail":detail})
    record("Python agent regression suite","local",lambda:check_command(
        [sys.executable,"-m","unittest","discover","-s","server","-p","test_*.py"],root))
    record("Project release static gate","local",lambda:check_command(
        [sys.executable,"scripts/release_gate.py"],root))
    record("Windows VNC RFB handshake","network",lambda:check_tcp("127.0.0.1",5900,True))
    record("noVNC HTTP page","network",lambda:check_http("http://127.0.0.1:6081/vnc.html"))
    record("noVNC WebSocket input and frame exchange","device")
    record("iPhone connected over Wi-Fi and cellular","device")
    record("iPhone zoom/pan and click accuracy","device")
    record("iPhone app launches and model inference runs","device")
    record("Authorized IPA decompilation and reconstruction","system")
    record("Signed reconstructed IPA launches and matches behavior","device")
    return {"schema":1,"generated_at":datetime.now(timezone.utc).isoformat(),
            "fully_verified":all(i["status"]=="PASS" for i in result),
            "results":result}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",type=pathlib.Path,default=pathlib.Path(__file__).resolve().parents[1])
    p.add_argument("--out",type=pathlib.Path,default=pathlib.Path("omniforge-system-audit.json"))
    args=p.parse_args()
    report=audit(args.root.resolve())
    args.out.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    md=["# OmniForge System Audit","","Overall: **"+("VERIFIED" if report["fully_verified"] else "INCOMPLETE")+"**","","| Test | Status | Details |","|---|---|---|"]
    for item in report["results"]:
        md.append("| "+item["name"]+" | "+item["status"]+" | "+item["detail"].replace("|","/").replace("\n"," ")+" |")
    args.out.with_suffix(".md").write_text("\n".join(md)+"\n",encoding="utf-8")
    print(json.dumps({"fully_verified":report["fully_verified"],"results":report["results"]},indent=2))
    return 0 if report["fully_verified"] else 2
if __name__=="__main__":sys.exit(main())
