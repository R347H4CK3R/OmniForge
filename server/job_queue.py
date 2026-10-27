"""Durable single-worker SQLite job queue for authorized agent tasks.

Runs locally. No automatic arbitrary shell execution or privilege escalation.
"""
import json
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

def now():
    return datetime.now(timezone.utc).isoformat()

class JobQueue:
    def __init__(self, filename):
        self.filename = str(Path(filename).resolve())
        Path(self.filename).parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        with self._db() as db:
            db.execute("CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, prompt TEXT NOT NULL, status TEXT NOT NULL, created TEXT NOT NULL, updated TEXT NOT NULL, result TEXT NOT NULL DEFAULT '', attempts INTEGER NOT NULL DEFAULT 0)")
            db.execute("CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status,created)")
            db.execute("UPDATE jobs SET status='queued', updated=? WHERE status='running'", (now(),))

    def _db(self):
        return sqlite3.connect(self.filename, timeout=30)

    def submit(self, prompt):
        if not isinstance(prompt,str) or not prompt.strip() or len(prompt)>20000:
            raise ValueError("Invalid prompt")
        jid=str(uuid.uuid4())
        with self.lock, self._db() as db:
            db.execute("INSERT INTO jobs(id,prompt,status,created,updated) VALUES(?,?,?,?,?)",
                       (jid,prompt,"queued",now(),now()))
        return jid

    def get(self, jid):
        with self.lock, self._db() as db:
            row=db.execute("SELECT id,prompt,status,created,updated,result,attempts FROM jobs WHERE id=?", (jid,)).fetchone()
        return dict(zip(["id","prompt","status","created","updated","result","attempts"],row)) if row else None

    def next(self):
        with self.lock, self._db() as db:
            db.execute("BEGIN IMMEDIATE")
            row=db.execute("SELECT id FROM jobs WHERE status='queued' ORDER BY created LIMIT 1").fetchone()
            if row:
                db.execute("UPDATE jobs SET status='running',updated=?,attempts=attempts+1 WHERE id=?",(now(),row[0]))
                claimed_id=row[0]
            else:
                claimed_id=None
        return self.get(claimed_id) if claimed_id else None

    def complete(self, jid, result, failed=False):
        with self.lock, self._db() as db:
            cursor=db.execute("UPDATE jobs SET status=?,result=?,updated=? WHERE id=? AND status='running'",
                            ("failed" if failed else "succeeded",str(result)[:100000],now(),jid))
            return cursor.rowcount==1

    def cancel(self, jid):
        with self.lock, self._db() as db:
            cursor=db.execute("UPDATE jobs SET status='cancelled',updated=? WHERE id=? AND status='queued'",(now(),jid))
            return cursor.rowcount==1

    def list(self, limit=30):
        with self.lock, self._db() as db:
            rows=db.execute("SELECT id,status,created,updated,attempts FROM jobs ORDER BY created DESC LIMIT ?",(min(max(int(limit),1),100),)).fetchall()
        return [dict(zip(["id","status","created","updated","attempts"],r)) for r in rows]
