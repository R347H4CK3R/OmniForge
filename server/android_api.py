"""Authenticated handler helpers for Android-specific workbench requests."""
import pathlib,sys,uuid
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'scripts'))
from android_workbench import inspect_apk,build_project,decompile_apk

def execute(workspace,body):
    root=pathlib.Path(workspace).resolve();value=body.get('path','');action=body.get('action')
    if action not in ('inspect','build','decompile'):raise ValueError('Unknown Android workbench action')
    if not isinstance(value,str) or not value or '\0' in value:raise ValueError('Invalid project path')
    target=(root/value).resolve()
    if target!=root and root not in target.parents:raise ValueError('Outside authorized workspace')
    if action=='inspect':return inspect_apk(target)
    if action=='build':return build_project(target)
    out=root/'AndroidAnalysis'/uuid.uuid4().hex
    return decompile_apk(target,out)
