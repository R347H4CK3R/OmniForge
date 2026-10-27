# Durable autonomous tasks

OmniForge now has a SQLite queue and worker that survives laptop-agent process restarts. Jobs are stored under `.omniforge-private/jobs.sqlite3`, excluded from Git. The worker requeues interrupted tasks; it does not resume an individual model step or roll back any preceding side effect. Avoid creating duplicate external resources on retry.

Start the model and the existing local agent normally, then run `python server/job_worker.py` on the laptop. For now, tasks may be submitted via the Python API:

```python
from server.job_queue import JobQueue
q=JobQueue(".omniforge-private/jobs.sqlite3")
print(q.submit("Inspect this authorized workspace and run available tests"))
```

Queued jobs execute sequentially using the current Ollama agent's existing workspace-scoped tools and preset test commands. They cannot bypass its execution limits, install arbitrary software, or access arbitrary files. Queue submission from the iPhone UI and notifications are **not yet implemented**.

Future steps: authenticated REST endpoints for enqueue/status/cancel, progress checkpoints, task-level step budgets, per-job approvals, an audit log, failure classification, retry-with-backoff, GitHub workflow polling, automated PR creation (not unreviewed default-branch changes), and iPhone progress/notification interface. A persistent worker requires the laptop to stay on.
