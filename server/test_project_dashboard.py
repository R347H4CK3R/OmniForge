"""Read-only project reporting must never mutate live work or claim a build passed."""
import http.client
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from unittest.mock import patch

from server import agent_server


class ProjectDashboardTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def report(self):
        from server.project_dashboard import build_report
        return build_report(self.root)

    def marker(self, name):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("untrusted project content; never execute", encoding="utf-8")

    def queue(self):
        path = self.root / ".omniforge-private/jobs.sqlite3"
        path.parent.mkdir()
        with sqlite3.connect(path) as db:
            db.execute("CREATE TABLE jobs (id TEXT, status TEXT, created TEXT, updated TEXT, attempts INTEGER, prompt TEXT, result TEXT)")
            db.execute("INSERT INTO jobs VALUES ('job-1', 'running', '2026-11-10', '2026-11-10', 1, 'private prompt', 'private result')")
        return path

    def test_detects_projects_without_claiming_verified_builds(self):
        self.marker("mobile/android/settings.gradle.kts")
        self.marker("mobile/project.yml")
        self.marker("web/package.json")
        self.marker("python/pyproject.toml")
        with patch("shutil.which", return_value=None), patch("platform.system", return_value="Windows"), patch.dict(os.environ, {}, clear=True):
            report = self.report()
        projects = {p["path"]: p for p in report["projects"]}
        self.assertEqual(set(projects), {"mobile", "python", "web"})
        self.assertEqual({t["platform"] for t in projects["mobile"]["targets"]}, {"android", "ios"})
        for project in projects.values():
            for target in project["targets"]:
                self.assertEqual(target["status"], "blocked")
                self.assertTrue(target["blockers"])
                self.assertFalse(target["build_verified"])
        self.assertFalse(report["execution_enabled"])
        self.assertEqual(report["remote_mac"]["status"], "not_configured")

    def test_detected_tools_do_not_mean_build_verified(self):
        self.marker("web/package.json")
        with patch("shutil.which", return_value="/fake/bin/tool"):
            target = self.report()["projects"][0]["targets"][0]
        self.assertEqual(target["status"], "prerequisites_detected")
        self.assertFalse(target["build_verified"])
        self.assertEqual(target["blockers"], [])

    def test_queue_read_preserves_running_job_and_redacts_content(self):
        path = self.queue()
        before = path.read_bytes()
        report = self.report()
        self.assertEqual(report["queue"]["status"], "available")
        self.assertEqual(report["queue"]["jobs"][0]["status"], "running")
        self.assertEqual(path.read_bytes(), before)
        self.assertNotIn("private prompt", json.dumps(report))
        self.assertNotIn("private result", json.dumps(report))
        self.assertNotIn(str(self.root), json.dumps(report))

    def test_missing_queue_is_not_created(self):
        report = self.report()
        self.assertEqual(report["queue"]["status"], "not_initialized")
        self.assertFalse((self.root / ".omniforge-private").exists())

    def test_corrupt_queue_is_visible_without_error_details(self):
        self.marker(".omniforge-private/jobs.sqlite3")
        report = self.report()
        self.assertEqual(report["queue"]["status"], "unavailable")
        self.assertNotIn(str(self.root), json.dumps(report))

    def test_external_symlinks_are_not_followed(self):
        with tempfile.TemporaryDirectory() as outside:
            Path(outside, "package.json").write_text("{}")
            try:
                (self.root / "external").symlink_to(outside, target_is_directory=True)
            except OSError:
                self.skipTest("Symlinks unavailable")
            self.assertEqual(self.report()["projects"], [])

    def test_external_queue_symlink_is_rejected(self):
        with tempfile.TemporaryDirectory() as outside:
            path = Path(outside, "jobs.sqlite3")
            path.write_text("not a database")
            (self.root / ".omniforge-private").mkdir()
            try:
                (self.root / ".omniforge-private/jobs.sqlite3").symlink_to(path)
            except OSError:
                self.skipTest("Symlinks unavailable")
            self.assertEqual(self.report()["queue"]["status"], "unavailable")

    def test_nested_external_project_markers_are_rejected(self):
        with tempfile.TemporaryDirectory() as outside:
            Path(outside, "settings.gradle.kts").write_text("private")
            (self.root / "mobile").mkdir()
            try:
                (self.root / "mobile/android").symlink_to(outside, target_is_directory=True)
            except OSError:
                self.skipTest("Symlinks unavailable")
            self.assertEqual(self.report()["projects"], [])

    def test_project_scan_is_bounded_and_marks_truncation(self):
        for index in range(105):
            self.marker(f"project-{index:03}/package.json")
        report = self.report()
        self.assertEqual(len(report["projects"]), 100)
        self.assertTrue(report["scan"]["truncated"])

    def test_queue_list_is_bounded(self):
        path = self.queue()
        with sqlite3.connect(path) as db:
            for i in range(35):
                db.execute("INSERT INTO jobs VALUES (?, 'queued', ?, '', 0, '', '')", (str(i), str(i)))
        report = self.report()
        self.assertEqual(len(report["queue"]["jobs"]), 30)
        self.assertTrue(report["queue"]["truncated"])

    def test_wal_queue_does_not_create_sidecars(self):
        path = self.queue()
        db = sqlite3.connect(path)
        db.execute("PRAGMA journal_mode=WAL")
        db.close()
        before = sorted(p.name for p in path.parent.iterdir())
        report = self.report()
        self.assertEqual(sorted(p.name for p in path.parent.iterdir()), before)
        self.assertEqual(report["queue"]["status"], "unavailable")

    def test_active_wal_queue_is_not_reported_from_stale_database(self):
        path = self.queue()
        db = sqlite3.connect(path)
        try:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("UPDATE jobs SET status='queued'")
            db.commit()
            before = {p.name: p.read_bytes() for p in path.parent.iterdir()}
            report = self.report()
            self.assertEqual(report["queue"]["status"], "unavailable")
            self.assertEqual({p.name: p.read_bytes() for p in path.parent.iterdir()}, before)
        finally:
            db.close()

    def test_queue_with_external_journal_symlink_is_rejected(self):
        path = self.queue()
        with tempfile.TemporaryDirectory() as outside:
            external = Path(outside, "journal")
            external.write_bytes(b"private external bytes")
            try:
                Path(str(path) + "-journal").symlink_to(external)
            except OSError:
                self.skipTest("Symlinks unavailable")
            self.assertEqual(self.report()["queue"]["status"], "unavailable")
            self.assertEqual(external.read_bytes(), b"private external bytes")

    def test_child_directory_scan_truncation_is_visible(self):
        folder = self.root / "ios"
        folder.mkdir()
        for i in range(105):
            (folder / f"entry-{i}").touch()
        (folder / "App.xcodeproj").mkdir()
        self.assertTrue(self.report()["scan"]["truncated"])

    def test_blob_queue_metadata_returns_sanitized_blocker(self):
        path = self.queue()
        with sqlite3.connect(path) as db:
            db.execute("UPDATE jobs SET id=?", (sqlite3.Binary(b"private bytes"),))
        report = self.report()
        self.assertEqual(report["queue"]["status"], "unavailable")
        self.assertNotIn("private bytes", json.dumps(report))

    def test_hidden_entries_count_toward_scan_budget(self):
        from server import project_dashboard
        from types import SimpleNamespace
        seen = []
        class Entries:
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def __iter__(self):
                for i in range(1000):
                    seen.append(i)
                    yield SimpleNamespace(name=f".hidden-{i}", path=str(self.root / f".hidden-{i}"))
        entries = Entries()
        entries.root = self.root
        with patch.object(project_dashboard.os, "scandir", return_value=entries):
            children, truncated = project_dashboard._bounded_children(self.root)
        self.assertLessEqual(len(seen), 101)
        self.assertTrue(truncated)
        self.assertEqual(children, [])

    def test_endpoint_requires_auth_and_does_not_cache(self):
        self.marker("private-project/package.json")
        server = ThreadingHTTPServer(("127.0.0.1", 0), agent_server.Handler)
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            with patch.object(agent_server, "KEY", "test-key"), patch.object(agent_server, "ROOT", self.root):
                for token, expected in ((None, 401), ("Bearer wrong", 401), ("Bearer test-key", 200)):
                    connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=3)
                    connection.request("GET", "/v1/projects", headers={} if token is None else {"Authorization": token})
                    response = connection.getresponse()
                    data = json.loads(response.read())
                    connection.close()
                    self.assertEqual(response.status, expected)
                    if expected == 200:
                        self.assertEqual(response.getheader("Cache-Control"), "no-store")
                        self.assertEqual(data["projects"][0]["path"], "private-project")
                    else:
                        self.assertNotIn("private-project", json.dumps(data))
        finally:
            server.shutdown()
            server.server_close()
            worker.join(timeout=3)


if __name__ == "__main__":
    unittest.main()
