"""Run jobs from the durable queue with the current OmniForge tool-constrained agent."""
import os
import time
from pathlib import Path
try:
    from job_queue import JobQueue
    from agent_server import ROOT, agent
except ImportError:
    from server.job_queue import JobQueue
    from server.agent_server import ROOT, agent

def process_one(queue):
    job=queue.next()
    if not job: return False
    try:
        reply=agent([{"role":"user","content":job["prompt"]}],os.environ.get("OLLAMA_MODEL","qwen3:8b"))
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
