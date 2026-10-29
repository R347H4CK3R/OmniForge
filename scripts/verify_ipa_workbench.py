#!/usr/bin/env python3
"""Verify the IPA workbench has produced evidence, a project, and a successful build.
This does not certify functional equivalence with the input application.
"""
from pathlib import Path
import json,sys
root=Path(sys.argv[1])
checks={
 "ipa_metadata":(root/"metadata.json").is_file() && (root/"file_inventory.txt").is_file(),
 "rebuild_decision":(root/"BuildDecision/decision.json").is_file(),
 "source_candidates_report":(root/"SourceDiscovery/source_candidates.json").is_file(),
 "clean_room_project":(root/"CleanRoomProject/project.yml").is_file(),
 "xcode_build_log":(root/"scaffold-build.log").is_file(),
}
log=root/"scaffold-build.log"
if log.exists():
    text=log.read_text(errors="replace")
    checks["scaffold_build_succeeded"]="** BUILD SUCCEEDED **" in text
report={
 "checks":{k:("PASS" if v else "FAIL") for k,v in checks.items()},
 "compiles_as_original_app":False,
 "equivalent_runtime_behavior_verified":False,
 "original_source_recovered":False,
 "note":"A compiling independent scaffold does not establish original app behavior."
}
(root/"verification.json").write_text(json.dumps(report,indent=2))
for k,v in checks.items():print(("PASS" if v else "FAIL")+": "+k)
if not all(checks.values()):sys.exit(1)
