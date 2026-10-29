"""OmniForge self-hosted agent. Python stdlib only; Ollama runs locally.
Invoke: python server/agent_server.py
Set OMNIFORGE_WORKSPACE, OMNIFORGE_AGENT_KEY, OLLAMA_URL, OLLAMA_MODEL.
"""
import json, os, pathlib, subprocess, urllib.request, urllib.error, hmac, shutil
try:
    from knowledge_vault import KnowledgeVault
except ImportError:
    from server.knowledge_vault import KnowledgeVault
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
try:
    from self_test import run_self_test
except ImportError:
    from server.self_test import run_self_test

ROOT=pathlib.Path(os.environ.get("OMNIFORGE_WORKSPACE", ".")).resolve()
KEY=os.environ.get("OMNIFORGE_AGENT_KEY","")
OLLAMA=os.environ.get("OLLAMA_URL","http://127.0.0.1:11434").rstrip("/")
MODEL=os.environ.get("OLLAMA_MODEL","qwen3:8b")
MAX_STEPS=12
MAX_BODY=100_000
ROOT.mkdir(parents=True,exist_ok=True)
VAULT=KnowledgeVault(ROOT / ".omniforge-private" / "knowledge.sqlite3")

def safe_path(value):
    if not isinstance(value,str) or not value or "\0" in value:
        raise ValueError("Invalid path")
    path=(ROOT/value).resolve()
    if path != ROOT and ROOT not in path.parents: raise ValueError("Outside authorized workspace")
    return path

def tool_run(name,args):
    if name=="list_files":
        folder=safe_path(args.get("path","."))
        return "\n".join(str(x.relative_to(ROOT)) for x in sorted(folder.iterdir())[:150])
    if name=="read_file":
        p=safe_path(args["path"])
        if p.stat().st_size>500_000: raise ValueError("File exceeds read limit")
        return p.read_text(encoding="utf-8")[:35000]
    if name=="write_file":
        p=safe_path(args["path"])
        data=args["content"]
        if not isinstance(data,str) or len(data)>100_000: raise ValueError("Write exceeds limit")
        p.parent.mkdir(parents=True,exist_ok=True)
        p.write_text(data,encoding="utf-8")
        return "Written "+str(p.relative_to(ROOT))
    if name=="run_check":
        # No arbitrary shell execution. Only explicitly enumerated non-destructive commands.
        presets={
            "git_status":["git","status","--short"],
            "git_diff":["git","diff","--stat"],
            "python_tests":["python","-m","unittest","discover","-s","tests"],
            "python_syntax":["python","-m","compileall","-q","server","scripts"],
        }
        key=args.get("check","")
        if key not in presets: raise ValueError("Unknown allowlisted check")
        proc=subprocess.run(presets[key],cwd=ROOT,text=True,capture_output=True,timeout=90,shell=False)
        return json.dumps({"returncode":proc.returncode,"stdout":proc.stdout[-12000:],"stderr":proc.stderr[-6000:]})
    if name=="knowledge_search":
        return json.dumps(VAULT.search(args.get("query","")))
    if name=="knowledge_import":
        file=safe_path(args["path"])
        if file.suffix.lower() not in (".json",".jsonl"): raise ValueError("Expected JSON or JSONL export")
        return json.dumps({"imported":VAULT.import_file(file)})
    if name=="workspace_info":
        return json.dumps({"root":str(ROOT),"allowed_checks":["git_status","git_diff","python_tests","python_syntax"]})
    raise ValueError("Tool unavailable")

SPECS=[{"type":"function","function":{"name":"list_files","description":"List files in an authorized workspace directory","parameters":{"type":"object","properties":{"path":{"type":"string"}},"required":["path"]}}},
{"type":"function","function":{"name":"read_file","description":"Read a UTF-8 source file","parameters":{"type":"object","properties":{"path":{"type":"string"}},"required":["path"]}}},
{"type":"function","function":{"name":"write_file","description":"Write a UTF-8 workspace file (user-authorized project only)","parameters":{"type":"object","properties":{"path":{"type":"string"},"content":{"type":"string"}},"required":["path","content"]}}},
{"type":"function","function":{"name":"run_check","description":"Execute a predefined non-destructive check","parameters":{"type":"object","properties":{"check":{"type":"string","enum":["git_status","git_diff","python_tests","python_syntax"]}},"required":["check"]}}},
{"type":"function","function":{"name":"knowledge_search","description":"Search local imported conversation knowledge","parameters":{"type":"object","properties":{"query":{"type":"string"}},"required":["query"]}}},
{"type":"function","function":{"name":"knowledge_import","description":"Import ChatGPT conversations.json or Codex JSONL from authorized workspace into private local database","parameters":{"type":"object","properties":{"path":{"type":"string"}},"required":["path"]}}},
{"type":"function","function":{"name":"workspace_info","description":"Describe workspace and allowed tools","parameters":{"type":"object","properties":{}}}}]

def ollama_chat(messages,model):
    payload=json.dumps({"model":model or MODEL,"messages":messages,"tools":SPECS,"stream":False}).encode()
    req=urllib.request.Request(OLLAMA+"/api/chat",data=payload,headers={"Content-Type":"application/json"})
    with urllib.request.urlopen(req,timeout=180) as response:
        return json.load(response)["message"]

def agent(messages,model):
    log=[]
    work=[{"role":"system","content":"You are OmniForge with REAL workspace tools and a persistent private knowledge vault. Search the knowledge vault when prior project context helps. Be careful not to claim unseen conversations were imported. Use tools to inspect, modify and test only the authorized workspace. Never invent outcomes. Do not claim success if checks fail. Do not execute arbitrary commands or access paths outside workspace. Limit changes to the user's request."}]
    work.extend({"role":m.get("role","user"),"content":str(m.get("content",""))[:16000]} for m in messages[-16:] if m.get("role") in ("user","assistant","system"))
    for i in range(MAX_STEPS):
        result=ollama_chat(work,model)
        calls=result.get("tool_calls") or []
        work.append(result)
        if not calls:
            answer=result.get("content","")
            return answer + ("\n\nTool execution report:\n"+ "\n".join(log) if log else "")
        for call in calls[:4]:
            f=call.get("function",{})
            name=f.get("name","")
            args=f.get("arguments",{})
            if isinstance(args,str):
                try: args=json.loads(args)
                except Exception: args={}
            try: output=tool_run(name,args);state="OK"
            except Exception as exc: output=str(exc);state="ERROR"
            log.append(f"{state} {name}: {str(output)[:160]}")
            work.append({"role":"tool","content":str(output)[:14000]})
    return "Step limit reached; review before continuing.\n" + "\n".join(log)

def remote_capabilities():
    """Honest, non-mutating report; installed executables do not establish an active session."""
    return {
        "schema": 1,
        "windows_host": {"agent_endpoint": "/v1/chat/completions",
                         "self_test_endpoint": "/v1/self-test",
                         "authenticated": bool(KEY),
                         "loopback_only": True},
        "network": {"tailscale_installed": shutil.which("tailscale") is not None,
                    "private_https_verified": False},
        "desktop": {"rustdesk_on_path": shutil.which("rustdesk") is not None,
                    "iphone_can_control_windows_verified": False},
        "iphone": {"replaykit_broadcast_implemented": False,
                   "windows_can_view_iphone_verified": False,
                   "windows_can_control_arbitrary_iphone_apps": False,
                   "omniforge_in_app_remote_commands_implemented": False},
        "note": "Availability is not session authorization or successful real-device verification."
    }

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path in ("/v1/self-test", "/v1/remote/capabilities"):
            if not KEY or not hmac.compare_digest(self.headers.get("Authorization",""),"Bearer "+KEY):
                self.reply(401,{"error":"Unauthorized"});return
            self.reply(200,remote_capabilities() if self.path=="/v1/remote/capabilities" else run_self_test(ROOT,OLLAMA,MODEL));return
        if self.path!="/health": self.send_error(404);return
        self.reply(200,{"ok":True,"model":MODEL,"workspace_configured":True,"tool_count":len(SPECS)})
    def do_POST(self):
        if self.path!="/v1/chat/completions":self.send_error(404);return
        if not KEY or not hmac.compare_digest(self.headers.get("Authorization",""),"Bearer "+KEY):
            self.reply(401,{"error":"Unauthorized"});return
        try:
            count=int(self.headers.get("Content-Length","0"))
            if not 0<count<=MAX_BODY:raise ValueError("Request too large")
            body=json.loads(self.rfile.read(count))
            if not isinstance(body.get("messages"),list):raise ValueError("Missing messages")
            last=next((str(m.get("content","")).strip().lower() for m in reversed(body["messages"]) if isinstance(m,dict) and m.get("role")=="user"),"")
            if last in ("/self-test","/selftest"):
                result=json.dumps(run_self_test(ROOT,OLLAMA,MODEL),indent=2)
            else:
                result=agent(body["messages"],body.get("model") or MODEL)
            self.reply(200,{"choices":[{"message":{"role":"assistant","content":result},"finish_reason":"stop","index":0}]})
        except Exception as e:self.reply(400,{"error":str(e)[:300]})
    def reply(self,status,data):
        raw=json.dumps(data).encode()
        self.send_response(status);self.send_header("Content-Type","application/json")
        self.send_header("Content-Length",str(len(raw)));self.end_headers();self.wfile.write(raw)

if __name__=="__main__":
    if not KEY:raise SystemExit("Set OMNIFORGE_AGENT_KEY before starting")
    print("OmniForge agent listening on 127.0.0.1:8787 (expose privately via Tailscale Serve)")
    ThreadingHTTPServer(("127.0.0.1",8787),Handler).serve_forever()
