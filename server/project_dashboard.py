"""Read-only project/build readiness. No commands, network calls or queue mutation."""
import argparse
from contextlib import closing
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import shutil
import sqlite3

MAX_DIRECTORIES = 100
MAX_JOBS = 30


def _inside(root, path):
    try:
        return path.resolve().is_relative_to(root)
    except (OSError, RuntimeError):
        return False


def _file(root, path):
    return _inside(root, path) and path.is_file()


def _targets(root, folder, tools):
    targets = []
    children, truncated = _bounded_children(folder)

    def add(name, blockers):
        targets.append({"platform": name,
                        "status": "blocked" if blockers else "prerequisites_detected",
                        "blockers": blockers, "build_verified": False})

    android = next((p for p in (folder, folder / "android")
                    if any(_file(root, p / marker) for marker in
                           ("settings.gradle", "settings.gradle.kts"))), None)
    if android is not None:
        blockers = []
        if not tools["java"]:
            blockers.append("Java is not on this host process's PATH; the Android bridge needs JDK 17.")
        if not tools["gradle"]:
            blockers.append("Gradle is not on this host process's PATH.")
        if not tools["android_sdk"]:
            blockers.append("Android SDK platforms and build-tools are not detected in ANDROID_HOME/ANDROID_SDK_ROOT.")
        add("android", blockers)

    # Do not enumerate arbitrary directory contents or parse untrusted project files.
    if _file(root, folder / "project.yml") or any(
            _inside(root, p) and p.is_dir()
            for p in children
            if p.suffix in (".xcodeproj", ".xcworkspace")):
        blockers = []
        if platform.system() != "Darwin":
            blockers.append("Local iOS builds require a Mac with Xcode; this host is not macOS.")
        elif not tools["xcodebuild"]:
            blockers.append("Xcode command-line build tools are not detected.")
        if _file(root, folder / "project.yml") and not tools["xcodegen"]:
            blockers.append("This XcodeGen project needs xcodegen on the build host.")
        add("ios", blockers)

    if _file(root, folder / "package.json"):
        add("web", [] if tools["node"] and tools["npm"] else
            ["Node.js and npm are required; a package manifest alone does not prove a web build works."])
    if any(_file(root, folder / marker) for marker in
           ("pyproject.toml", "setup.py", "requirements.txt")):
        add("python", [] if tools["python"] else ["Python is not on this host process's PATH."])
    return targets, truncated


def _bounded_children(folder):
    children = []
    # Bound entries, including files, so an unusually large directory stays cheap.
    with os.scandir(folder) as entries:
        for count, entry in enumerate(entries):
            if count == MAX_DIRECTORIES:
                return children, True
            if entry.name.startswith("."):
                continue
            children.append(Path(entry.path))
    return children, False


def _queue(root):
    path = root / ".omniforge-private" / "jobs.sqlite3"
    unavailable = {"status": "unavailable", "jobs": [], "truncated": False,
                   "blocker": "Queue metadata could not be read safely; existing jobs were not changed."}
    if not _inside(root, path):
        return unavailable
    if not path.exists():
        return {"status": "not_initialized", "jobs": [], "truncated": False}
    try:
        # SQLite mode=ro can create WAL sidecars. Do not read WAL databases or
        # pending recovery state: immutable=1 would hide uncheckpointed jobs.
        with path.open("rb") as source:
            header = source.read(20)
        if header[18:20] != b"\x01\x01" or any(
                Path(str(path) + suffix).exists() or Path(str(path) + suffix).is_symlink()
                for suffix in ("-wal", "-shm", "-journal")):
            return unavailable
        # Do not instantiate JobQueue: its constructor requeues running jobs.
        with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True, timeout=1)) as db:
            db.execute("PRAGMA query_only=ON")
            # Keep scan work bounded even if a damaged/unexpected database has no index.
            db.set_progress_handler(lambda: 1, 100000)
            rows = db.execute(
                "SELECT substr(id,1,100), substr(status,1,40), substr(created,1,50), "
                "substr(updated,1,50), attempts FROM jobs ORDER BY created DESC LIMIT ?",
                (MAX_JOBS + 1,)).fetchall()
        if any(not all(isinstance(value, str) for value in row[:4]) or
               not isinstance(row[4], int) or not 0 <= row[4] <= 2**31 - 1
               for row in rows):
            return unavailable
        keys = ("id", "status", "created", "updated", "attempts")
        return {"status": "available", "jobs": [dict(zip(keys, row)) for row in rows[:MAX_JOBS]],
                "truncated": len(rows) > MAX_JOBS,
                "note": "Stored status only; worker liveness and build success are not verified."}
    except (OSError, sqlite3.Error, ValueError):
        return unavailable


def _tools():
    result = {name: shutil.which(name) is not None for name in
              ("git", "java", "gradle", "node", "npm", "python", "xcodebuild", "xcodegen")}
    if not result["python"]:
        result["python"] = shutil.which("python3") is not None
    result["android_sdk"] = False
    for variable in ("ANDROID_HOME", "ANDROID_SDK_ROOT"):
        value = os.environ.get(variable)
        if value:
            sdk = Path(value)
            if (sdk / "platforms").is_dir() and (sdk / "build-tools").is_dir():
                result["android_sdk"] = True
    return result


def build_report(workspace):
    root = Path(workspace).resolve()
    tools = _tools()
    projects = []
    blockers = []
    truncated = False
    try:
        children, truncated = _bounded_children(root)
        folders = [root] + sorted((p for p in children if _inside(root, p) and p.is_dir()), key=lambda p: p.name.casefold())
        for folder in folders:
            targets, child_truncated = _targets(root, folder, tools)
            truncated = truncated or child_truncated
            if targets:
                projects.append({"path": folder.relative_to(root).as_posix(), "targets": targets})
    except (OSError, RuntimeError):
        blockers.append("Some project folders could not be inspected; this report may be incomplete.")
    return {
        "schema": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "read_only": True,
        "execution_enabled": False,
        "host": {"os": platform.system(), "tools_detected": tools},
        "scan": {"scope": "Workspace root and up to 100 immediate entries only; hidden entries are not inspected",
                 "truncated": truncated, "blockers": blockers},
        "projects": projects,
        "queue": _queue(root),
        "remote_mac": {"status": "not_configured", "build_verified": False,
                       "blocker": "No remote Mac dispatcher is configured in this report. A Windows server can coordinate a Mac, but cannot run Xcode itself."},
        "note": "Detection is not a successful build. No jobs, files, accounts, credentials or billing settings are changed. No automatic app update or installation is enabled."
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workspace", nargs="?", default=os.environ.get("OMNIFORGE_WORKSPACE", "."))
    args = parser.parse_args()
    print(json.dumps(build_report(args.workspace), indent=2))


if __name__ == "__main__":
    main()
