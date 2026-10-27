#!/usr/bin/env python3
"""OmniForge release gate: reject obvious incomplete-feature claims and broken project wiring."""
from pathlib import Path
import sys, ast, json
root=Path(__file__).resolve().parents[1]
required=[
 "App/OmniForgeApp.swift","App/MainView.swift","App/AssistantStore.swift",
 "App/LocalCodingAgent.swift","App/OmniToolCatalog.swift",
 "App/OmniDocumentPicker.swift","App/IPAInspector.swift","App/IPAWorkbench.swift",
 "App/OmniSearch.swift","App/OnlineModelClient.swift",
 "project.yml",".github/workflows/livecontainer-publish.yml"
]
problems=[]
for name in required:
    if not (root/name).is_file():problems.append("Missing "+name)
for path in (root/"scripts").glob("*.py"):
    try:ast.parse(path.read_text(encoding="utf-8"),filename=str(path))
    except SyntaxError as error:problems.append(f"{path.name}:{error.lineno}: {error.msg}")
for path in (root/"server").glob("*.py"):
    try:ast.parse(path.read_text(encoding="utf-8"),filename=str(path))
    except SyntaxError as error:problems.append(f"{path.name}:{error.lineno}: {error.msg}")
catalog=json.loads((root/"livecontainer-source.json").read_text())
if not isinstance(catalog.get("apps"),list):problems.append("Invalid app catalog")
print("Release gate file and Python syntax audit")
for p in problems:print("FAIL:",p)
if problems:sys.exit(1)
print("PASS: static audit. This does NOT prove runtime tool behavior or device functionality.")
