#!/usr/bin/env python3
"""Local Windows dependency installer; serve only on loopback behind a private HTTPS reverse proxy.
Environment: OMNIFORGE_INSTALL_TOKEN (long random secret), optional OMNIFORGE_PORT.
No arbitrary command endpoint. Every install is package-allowlisted.
"""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit, parse_qs
import os, json, hmac, shutil, subprocess, threading

CATALOG = {
    "github-cli": ("GitHub.cli", "gh"),
    "git": ("Git.Git", "git"),
    "python": ("Python.Python.3.13", "python"),
    "7zip": ("7zip.7zip", "7z"),
}
LOCK = threading.Lock()
TOKEN = os.environ.get("OMNIFORGE_INSTALL_TOKEN", "")
if len(TOKEN) < 32:
    raise SystemExit("Set OMNIFORGE_INSTALL_TOKEN to at least 32 random characters.")

def which(tool):
    # Some installations require a new PATH; search known install directories too.
    resolved = shutil.which(tool)
    if resolved:
        return resolved
    if os.name == "nt":
        guesses = {
            "gh": [r"C:\Program Files\GitHub CLI\gh.exe"],
            "git": [r"C:\Program Files\Git\cmd\git.exe"],
            "7z": [r"C:\Program Files\7-Zip\7z.exe"]
        }
        for path in guesses.get(tool, []):
            if os.path.isfile(path):
                return path
    return None

class Handler(BaseHTTPRequestHandler):
    def reply(self, code, obj):
        data = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def dispatch(self):
        auth = self.headers.get("Authorization", "")
        if not hmac.compare_digest(auth, "Bearer " + TOKEN):
            return self.reply(401, {"error": "unauthorized"})
        parsed = urlsplit(self.path)
        parts = parsed.path.rstrip("/").split("/")
        operation = parts[-1]
        package = parse_qs(parsed.query).get("package", [""])[0]
        if package not in CATALOG or operation not in ("status", "install"):
            return self.reply(404, {"error": "unknown package or operation"})
        pkg_id, exe = CATALOG[package]
        if operation == "status":
            return self.reply(200, {"package": package, "installed": bool(which(exe)), "executable": which(exe)})
        if self.command != "POST":
            return self.reply(405, {"error": "POST required"})
        if not LOCK.acquire(blocking=False):
            return self.reply(409, {"error": "installation already running"})
        try:
            existing = which(exe)
            if existing:
                return self.reply(200, {"package": package, "installed": True, "verified": True, "executable": existing})
            # WinGet package IDs are fixed; no user-supplied executable or arguments.
            result = subprocess.run(
                ["winget", "install", "--id", pkg_id, "--exact",
                 "--silent", "--accept-source-agreements", "--accept-package-agreements"],
                capture_output=True, text=True, timeout=600, shell=False)
            found = which(exe)
            return self.reply(200 if result.returncode == 0 and found else 500, {
                "package": package, "installer_exit": result.returncode,
                "installed": bool(found), "verified": bool(found),
                "output": (result.stdout + "\n" + result.stderr)[-6000:]})
        except (OSError, subprocess.TimeoutExpired) as e:
            return self.reply(500, {"error": str(e)})
        finally:
            LOCK.release()

    def do_GET(self): self.dispatch()
    def do_POST(self): self.dispatch()
    def log_message(self, format, *args): pass

if __name__ == "__main__":
    if os.name != "nt":
        raise SystemExit("Windows only")
    port = int(os.environ.get("OMNIFORGE_PORT", "8767"))
    print("Listening on 127.0.0.1:%d. Put behind authenticated private HTTPS proxy." % port)
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
