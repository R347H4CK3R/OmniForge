"""Execute explicit, allowlisted behavior probes and record observed results.

This is an automated test runner, not proof of equivalence beyond specified tests.
Probes are fixed command types; no arbitrary shell strings are evaluated.
"""
import hashlib
import json
import pathlib
import subprocess
from datetime import datetime, timezone

def run_probes(project, evidence, timeout=120):
    project=pathlib.Path(project).resolve()
    evidence=pathlib.Path(evidence).resolve()
    manifest=json.loads((evidence/"acceptance.json").read_text(encoding="utf-8"))
    requirements=manifest["requirements"]
    if not isinstance(requirements,list) or not requirements or len(requirements)>100:
        raise ValueError("Expected 1-100 explicit behavior probes")
    cases=[]
    for requirement in requirements:
        ident=requirement["id"]
        kind=requirement.get("type")
        try:
            if kind=="file_sha256":
                relative=pathlib.PurePosixPath(requirement["path"])
                candidate=(project/str(relative)).resolve()
                if candidate==project or project not in candidate.parents or not candidate.is_file():
                    raise ValueError("File outside project or missing")
                expected=requirement["sha256"].lower()
                if len(expected)!=64 or any(c not in "0123456789abcdef" for c in expected):
                    raise ValueError("Invalid digest")
                digest=hashlib.file_digest(candidate.open("rb"),"sha256").hexdigest()
                passed=digest==expected
                detail="SHA256: "+digest
            elif kind=="python_unittest":
                # Explicit project-local test module path, not user-provided shell.
                folder=(project/"tests").resolve()
                if not folder.is_dir(): raise ValueError("No project tests directory")
                process=subprocess.run(["python","-m","unittest","discover","-s","tests","-p","test_*.py"],
                    cwd=project,capture_output=True,text=True,shell=False,timeout=timeout)
                passed=process.returncode==0
                detail=(process.stdout+"\n"+process.stderr)[-2500:]
            else:
                raise ValueError("Unsupported probe type")
            cases.append({"id":ident,"status":"PASS" if passed else "FAIL",
                          "evidence":detail or "Completed without output"})
        except (OSError,ValueError,KeyError,subprocess.TimeoutExpired) as error:
            cases.append({"id":ident,"status":"FAIL","evidence":"Probe failed: "+str(error)[:500]})
    result={"schema":1,"executed_at":datetime.now(timezone.utc).isoformat(),
            "runner":"omniforge-behavior-probes","cases":cases}
    (project/"acceptance-results.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
    return result
