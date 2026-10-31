"""Smoke checks for OmniForge's allowlisted Windows installer bridge.
Never starts installs, requires no real credentials and listens only on loopback.
"""
import importlib.util
import json
import os
import pathlib
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

os.environ["OMNIFORGE_INSTALL_TOKEN"] = "local-smoke-test-token-no-public-access-0123456789"
source = pathlib.Path(__file__).resolve().parents[1] / "bridge" / "omniforge_installer.py"
spec = importlib.util.spec_from_file_location("omniforge_installer", source)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

server = ThreadingHTTPServer(("127.0.0.1", 0), module.Handler)
thread = threading.Thread(target=server.serve_forever, daemon=True)
thread.start()
base = "http://127.0.0.1:" + str(server.server_port)
token = os.environ["OMNIFORGE_INSTALL_TOKEN"]

def check(path, expected, method="GET", authorized=True):
    req = urllib.request.Request(base + path, method=method)
    if authorized:
        req.add_header("Authorization", "Bearer " + token)
    try:
        with urllib.request.urlopen(req, timeout=5) as res:
            code = res.status
            obj = json.loads(res.read())
    except urllib.error.HTTPError as e:
        code = e.code
        obj = json.loads(e.read())
    assert code == expected, (path, code, obj)
    return obj

try:
    assert check("/status?package=github-cli", 401, authorized=False)["error"] == "unauthorized"
    assert check("/status?package=unknown", 404)["error"]
    assert check("/install?package=github-cli", 405)["error"]
    assert check("/status?package=git", 200)["package"] == "git"
    assert "installed" in check("/status?package=python", 200)
    print("PASS: unauthorized rejected, unknown rejected, GET install rejected, status accepted")
finally:
    server.shutdown()
    server.server_close()
