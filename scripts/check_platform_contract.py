"""Validate the shared feature contract and both native application identities."""
import json,pathlib
ROOT=pathlib.Path(__file__).resolve().parents[1]
data=json.loads((ROOT/'shared/features.json').read_text())
assert data['schema']==1
assert len(data['common'])==len(set(data['common']))
assert (ROOT/data['ios']['source']/'OmniForgeApp.swift').is_file()
assert (ROOT/data['android']['source']/'app/src/main/AndroidManifest.xml').is_file()
assert data['ios']['application_id'] in (ROOT/'project.yml').read_text()
assert data['android']['application_id'] in (ROOT/'android/app/build.gradle.kts').read_text()
print('PASS: shared contract and both native app identities (not runtime parity)')
