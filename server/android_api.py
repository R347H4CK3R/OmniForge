"""Authenticated handler helpers for Android-specific workbench requests."""
import pathlib,sys,uuid
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'scripts'))
from android_workbench import inspect_apk,build_project,decompile_apk,decode_resources,rebuild_resources

def execute(workspace,body):
    root=pathlib.Path(workspace).resolve();value=body.get('path','');action=body.get('action')
    if action not in ('inspect','build','decompile','decode','rebuild'):raise ValueError('Unknown Android workbench action')
    if not isinstance(value,str) or not value or '\0' in value:raise ValueError('Invalid project path')
    target=(root/value).resolve()
    if target!=root and root not in target.parents:raise ValueError('Outside authorized workspace')
    if action=='inspect':return inspect_apk(target)
    if action=='build':
        result=build_project(target)
        for artifact in result.get('artifacts',[]):artifact['path']=str((target/artifact['path']).relative_to(root))
        return result
    if action=='rebuild':return rebuild_resources(target,root)
    out=root/'AndroidAnalysis'/uuid.uuid4().hex
    if action=='decode':return decode_resources(target,out)
    return decompile_apk(target,out)

def download_path(workspace,value):
    root=pathlib.Path(workspace).resolve();target=(root/value).resolve()
    if root not in target.parents or target.suffix.lower()!='.apk' or not target.is_file():raise ValueError('Invalid APK artifact path')
    return target
