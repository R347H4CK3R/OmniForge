"""Launch the optional Android workbench with private laptop configuration."""
import json,os,pathlib,runpy,sys
base=pathlib.Path(os.environ['LOCALAPPDATA'])/'OmniForge'
log=(base/'AndroidHost/server.log').open('a',encoding='utf-8',buffering=1)
sys.stdout=log;sys.stderr=log
tools=json.loads((base/'AndroidTools/environment.json').read_text())
os.environ.update(tools)
sdk=pathlib.Path(tools['ANDROID_HOME']);java=pathlib.Path(tools['JAVA_HOME'])
os.environ['PATH']=os.pathsep.join([str(java/'bin'),str(pathlib.Path(tools['GRADLE_HOME'])/'bin'),str(sdk/'build-tools/35.0.0'),str(sdk/'platform-tools'),os.environ['PATH']])
os.environ['OMNIFORGE_AGENT_KEY']=(base/'agent-key.txt').read_text(encoding='utf-8-sig').strip()
os.environ['OMNIFORGE_WORKSPACE']=str(base/'Workspace')
keys=base/'AndroidHostKeys'
if (keys/'development.jks').is_file():
    os.environ['ANDROID_WORKBENCH_KEYSTORE']=str(keys/'development.jks')
    os.environ['ANDROID_WORKBENCH_PASSWORD_FILE']=str(keys/'password.txt')
server=base/'AndroidHost/server'
sys.path.insert(0,str(server))
runpy.run_path(str(server/'android_host.py'),run_name='__main__')
