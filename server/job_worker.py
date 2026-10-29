"""Run jobs from the durable queue with the current OmniForge tool-constrained agent."""
import os
import time
import json
from pathlib import Path
try:
    from job_queue import JobQueue
    from agent_server import ROOT, agent
    from build_repair import repair_build
    from autonomous_reconstruction import reconstruct
except ImportError:
    from server.job_queue import JobQueue
    from server.agent_server import ROOT, agent
    from server.build_repair import repair_build
    from server.autonomous_reconstruction import reconstruct

def process_one(queue):
    job=queue.next()
    if not job: return False
    try:
        prompt=job["prompt"]
        if prompt.strip().lower().startswith("reconstruct:"):
            # Existing, user-authorized project and evidence must be under the workspace.
            # Format: reconstruct: relative-project-path | relative-evidence-path
            from pathlib import Path
            values=prompt.split(":",1)[1].split("|")
            if len(values)!=2: raise ValueError("Expected reconstruct: project | evidence")
            def confined(value):
                candidate=(Path(ROOT)/value.strip()).resolve()
                if candidate==Path(ROOT) or Path(ROOT) not in candidate.parents:
                    raise ValueError("Reconstruction path outside workspace")
                return candidate
            project,evidence=map(confined,values)
            result=reconstruct(project,evidence,lambda instruction: agent(
                [{"role":"user","content":instruction}],os.environ.get("OLLAMA_MODEL","qwen3:8b")))
            queue.complete(job["id"],json.dumps(result),failed=not result["compiled"])
        elif prompt.strip().lower().startswith("build:"):
            task=prompt.split(":",1)[1].strip()
            result=repair_build(task, ROOT, lambda instruction: agent(
                [{"role":"user","content":instruction}],os.environ.get("OLLAMA_MODEL","qwen3:8b")))
            queue.complete(job["id"],json.dumps(result),failed=not result["success"])
        else:
            reply=agent([{"role":"user","content":prompt}],os.environ.get("OLLAMA_MODEL","qwen3:8b"))
            queue.complete(job["id"],reply)
    except Exception as exc:
        queue.complete(job["id"],str(exc),failed=True)
    return True

def main():
    queue=JobQueue(Path(ROOT)/".omniforge-private"/"jobs.sqlite3")
    print("OmniForge local job worker started; Ctrl+C to stop")
    while True:
        if not process_one(queue):
            time.sleep(2)

if __name__=="__main__":
    main()
