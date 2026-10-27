import tempfile
import unittest
from pathlib import Path
try:
    from job_queue import JobQueue
except ImportError:
    from server.job_queue import JobQueue

class QueueTests(unittest.TestCase):
    def test_state_transitions(self):
        with tempfile.TemporaryDirectory() as temp:
            q=JobQueue(Path(temp)/"jobs.db")
            job=q.submit("Check GitHub logs")
            self.assertEqual(q.get(job)["status"],"queued")
            claimed=q.next()
            self.assertEqual(claimed["id"],job)
            self.assertEqual(q.get(job)["attempts"],1)
            self.assertTrue(q.complete(job,"done"))
            self.assertEqual(q.get(job)["result"],"done")
            self.assertIsNone(q.next())
    def test_recovery_and_cancel(self):
        with tempfile.TemporaryDirectory() as temp:
            file=Path(temp)/"jobs.db"
            q=JobQueue(file)
            job=q.submit("Inspect IPA")
            q.next()
            restarted=JobQueue(file)
            self.assertEqual(restarted.get(job)["status"],"queued")
            self.assertTrue(restarted.cancel(job))
            self.assertIsNone(restarted.next())
    def test_reject_empty(self):
        with tempfile.TemporaryDirectory() as temp:
            q=JobQueue(Path(temp)/"jobs.db")
            with self.assertRaises(ValueError): q.submit(" ")
if __name__=="__main__": unittest.main()
