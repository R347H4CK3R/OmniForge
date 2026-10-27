"""Read-only, bounded OmniForge diagnostic checks. No destructive test operations."""
import json, os, pathlib, shutil, sqlite3, subprocess, tempfile, urllib.request
from datetime import datetime, timezone

def check(name, fn):
    try:
        status, detail=fn()
        return {"name":name,"status":status,"detail":str(detail)[:500]}
    except Exception as exc:
        return {"name":name,"status":"FAIL","detail":str(exc)[:500]}

def run_self_test(workspace, ollama_url="http://127.0.0.1:11434", model="qwen3:8b"):
    root=pathlib.Path(workspace).resolve()
    results=[]
    def filesystem():
        with tempfile.TemporaryDirectory(prefix=".omniforge-test-",dir=root) as folder:
            p=pathlib.Path(folder)/"test.json"
            p.write_text('{"ok":true}',encoding="utf-8")
            assert json.loads(p.read_text(encoding="utf-8"))["ok"]
        return "PASS","Atomic workspace smoke test passed"
    results.append(check("workspace",filesystem))
    def database(name):
        file=root/".omniforge-private"/name
        if not file.exists(): return "SKIP","Database not initialized"
        with sqlite3.connect(str(file)) as db:
            ok=db.execute("PRAGMA quick_check").fetchone()[0]
        if ok!="ok": return "FAIL",ok
        return "PASS","SQLite integrity verified"
    results.append(check("knowledge_database",lambda:database("knowledge.sqlite3")))
    results.append(check("job_database",lambda:database("jobs.sqlite3")))
    def ollama():
        try:
            with urllib.request.urlopen(ollama_url.rstrip("/")+"/api/tags",timeout=4) as response:
                data=json.load(response)
            names=[m.get("name","") for m in data.get("models",[])]
            if not names: return "FAIL","Ollama running, no models installed"
            if model not in names and not any(n.startswith(model+":") for n in names):
                return "FAIL",f"Selected model {model} not installed; found {len(names)} model(s)"
            return "PASS",f"Ollama reachable; {len(names)} model(s)"
        except Exception as exc:
            return "FAIL","Ollama not reachable: "+str(exc)[:200]
    results.append(check("ollama_model",ollama))
    for name,cmd in (("git","git"),("python","python"),("node","node"),("llvm","clang"),("tailscale","tailscale")):
        results.append(check("tool_"+name,lambda command=cmd:("PASS" if shutil.which(command) else "SKIP",shutil.which(command) or "Not installed")))
    def configured():
        return ("PASS" if os.environ.get("OMNIFORGE_AGENT_KEY") else "FAIL","Agent access key configured" if os.environ.get("OMNIFORGE_AGENT_KEY") else "Missing access key")
    results.append(check("agent_authentication",configured))
    statuses=[r["status"] for r in results]
    return {"schema":1,"generated_at":datetime.now(timezone.utc).isoformat(),"device":"windows-host","overall":"FAIL" if "FAIL" in statuses else "PASS" if "SKIP" not in statuses else "PARTIAL","counts":{s:statuses.count(s) for s in ("PASS","FAIL","SKIP")},"checks":results,"note":"Smoke test only: no macOS runner, real IPA install, or remote iPhone pairing is verified here."}
