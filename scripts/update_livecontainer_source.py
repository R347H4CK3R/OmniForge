#!/usr/bin/env python3
"""Publish only an already-uploaded GitHub Release IPA into a LiveContainer/AltStore catalog."""
import datetime, json, os, pathlib, sys
tag, build, filename, out = sys.argv[1:]
assert tag.startswith("lc-") and build.isdigit()
assert filename == "OmniForge-LiveContainer.ipa"
path = pathlib.Path(filename)
size = path.stat().st_size
assert 1_000_000 < size < 2_000_000_000
url = f"https://github.com/R347H4CK3R/OmniForge/releases/download/{tag}/{filename}"
target = pathlib.Path(out)
if target.exists():
    source = json.loads(target.read_text())
else:
    source = {"name": "OmniForge LiveContainer", "identifier": "com.r347h4ck3r.omniforge.source",
              "subtitle": "Offline AI developer tools", "iconURL": "https://github.com/R347H4CK3R.png", "description": "Unsigned LiveContainer IPA updates.", "apps": [], "news": []}
app = {"name": "OmniForge", "bundleIdentifier": "com.r347h4ck3r.omniforge",
       "developerName": "R347H4CK3R", "subtitle": "Offline AI development workbench",
       "localizedDescription": "Imports local GGUF models; analyzes IPA and development files.",
       "versions": [], "tintColor": "4065B5", "iconURL": "https://github.com/R347H4CK3R.png", "category": "developer", "appPermissions": {"entitlements": [], "privacy": {}}}
existing = next((item for item in source.get("apps", []) if item.get("bundleIdentifier") == app["bundleIdentifier"]), None)
if existing:
    app.update(existing)
version = {"version": f"1.0.{build}", "buildVersion": build,
           "date": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
           "localizedDescription": f"LiveContainer update {build}",
           "downloadURL": url, "size": size, "minOSVersion": "17.0"}
app["versions"] = sorted(
    [version] + [v for v in app.get("versions", []) if v.get("buildVersion") != build],
    key=lambda v: int(v.get("buildVersion", 0)), reverse=True
)[:10]
version = app["versions"][0]
url = version["downloadURL"]
size = version["size"]
app["iconURL"] = f"https://github.com/R347H4CK3R/OmniForge/releases/download/lc-{version['buildVersion']}/OmniForgeIcon.png"
source["iconURL"] = app["iconURL"]
app["downloadURL"] = url
app["version"] = version["version"]
app["versionDate"] = version["date"]
app["size"] = size
source["apps"] = [app]
target.write_text(json.dumps(source, indent=2) + "\n")
print(f"Published {tag} {size} bytes")
