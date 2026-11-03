"""Authenticated handler helpers for Android-specific workbench requests."""
import pathlib,sys,uuid
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'scripts'))
from android_workbench import inspect_apk,build_project,decompile_apk,decode_resources,rebuild_resources

def execute(workspace,body):
    root=pathlib.Path(workspace).resolve();value=body.get('path','');action=body.get('action')
    if action not in ('inspect','build','decompile','decode','rebuild','read_file','write_file','list_files'):raise ValueError('Unknown Android workbench action')
    if not isinstance(value,str) or not value or '\0' in value:raise ValueError('Invalid project path')
    target=(root/value).resolve()
    if target!=root and root not in target.parents:raise ValueError('Outside authorized workspace')
    if action=='list_files':return {'files':[p.name for p in sorted(target.iterdir())][:150]}
    if action in ('read_file','write_file'):
        if target.suffix.lower() not in ('.kt','.java','.gradle','.kts','.xml','.yml','.yaml','.json','.txt','.properties','.smali','.md'):raise ValueError('Only source/configuration text files may be edited')
        if action=='read_file':
            if target.stat().st_size>500000:raise ValueError('File too large')
            return {'content':target.read_text(encoding='utf-8')}
        content=body.get('content')
        if not isinstance(content,str) or len(content.encode('utf-8'))>500000:raise ValueError('Invalid or oversized source content')
        target.parent.mkdir(parents=True,exist_ok=True);target.write_text(content,encoding='utf-8');return {'written':str(target.relative_to(root))}
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

def complete(body,default_model,ollama='http://127.0.0.1:11434',opener=None):
    """Raw structured completion for the Android-owned tool loop; never nest the host agent."""
    import json,urllib.request
    messages=body.get('messages')
    if not isinstance(messages,list) or not messages:raise ValueError('Missing conversation messages')
    schema={'oneOf':[
        {'type':'object','properties':{'answer':{'type':'string'}},'required':['answer'],'additionalProperties':False},
        {'type':'object','properties':{'tool':{'type':'string','enum':['list_files','read_file','write_file','validate_json','inspect_apk','fetch_https','host_build_source','host_analyze_apk','host_action']},'args':{'type':'object'}},'required':['tool','args'],'additionalProperties':False}
    ]}
    payload={'model':body.get('model') or default_model,'messages':messages,'stream':False,'format':schema,'keep_alive':'30s','options':{'temperature':0,'num_ctx':8192,'num_predict':2048}}
    req=urllib.request.Request(ollama.rstrip('/')+'/api/chat',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
    with (opener or urllib.request.urlopen)(req,timeout=300) as response:
        raw=response.read(2_000_001)
        if len(raw)>2_000_000:raise ValueError('Model response exceeds limit')
        data=json.loads(raw)
    text=data.get('message',{}).get('content','')
    if not text:raise ValueError('Model returned no content')
    return {'model':data.get('model') or payload['model'],'choices':[{'index':0,'message':{'role':'assistant','content':text},'finish_reason':'stop'}]}
