"""Install portable Android development tools for the private OmniForge workbench.
No startup services or system-wide PATH modifications. Run on the authorized Windows host.
"""
import hashlib,json,os,pathlib,subprocess,urllib.request,zipfile,xml.etree.ElementTree as ET
ROOT=pathlib.Path(os.environ['LOCALAPPDATA'])/'OmniForge'/'AndroidTools'
ROOT.mkdir(parents=True,exist_ok=True)
def get(url):
    with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'OmniForge'}),timeout=90) as r:return r.read()
def fetch(url,dest,digest=None):
    if dest.exists():return
    tmp=dest.with_suffix('.part')
    h=hashlib.sha256()
    with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'OmniForge'}),timeout=120) as r,tmp.open('wb') as out:
        for block in iter(lambda:r.read(128*1024),b''):out.write(block);h.update(block)
    if digest and h.hexdigest()!=digest:tmp.unlink();raise ValueError('Tool download hash mismatch')
    tmp.replace(dest)
def unpack(file,out):
    with zipfile.ZipFile(file) as z:
        for n in z.namelist():
            if '..' in pathlib.PurePosixPath(n).parts or n.startswith('/') or '\\' in n:raise ValueError('Unsafe tool archive')
        z.extractall(out)
def release(repo,match):
    r=json.loads(get('https://api.github.com/repos/'+repo+'/releases/latest'))
    a=next(a for a in r['assets'] if match(a['name']))
    return a['browser_download_url'],(a.get('digest') or '').removeprefix('sha256:') or None
print('Installing portable JDK, Gradle and Android SDK (no system services)',flush=True)
jdk=next(ROOT.glob('jdk-*/bin/java.exe'),None)
if not jdk:
    a=json.loads(get('https://api.adoptium.net/v3/assets/latest/17/hotspot?architecture=x64&image_type=jdk&os=windows'))[0]['binary']['package']
    f=ROOT/'jdk.zip';fetch(a['link'],f,a['checksum']);unpack(f,ROOT);jdk=next(ROOT.glob('jdk-*/bin/java.exe'))
java_home=jdk.parent.parent
sdk=ROOT/'sdk';sdk.mkdir(exist_ok=True)
manager=sdk/'cmdline-tools/latest/bin/sdkmanager.bat'
if not manager.exists():
    xml=ET.fromstring(get('https://dl.google.com/android/repository/repository2-1.xml'))
    package=next(e for e in xml.iter() if e.tag.endswith('remotePackage') and e.get('path')=='cmdline-tools;latest')
    archives=[e for e in package.iter() if e.tag.endswith('archive')]
    archive=next(e for e in archives if any(x.tag.endswith('host-os') and x.text=='windows' for x in e.iter()))
    url=next(x.text for x in archive.iter() if x.tag.endswith('url'))
    f=ROOT/'commandline.zip';fetch('https://dl.google.com/android/repository/'+url,f);stage=ROOT/'sdk-stage';unpack(f,stage)
    manager.parent.parent.parent.mkdir(parents=True,exist_ok=True)
    (stage/'cmdline-tools').replace(manager.parent.parent)
gradle=ROOT/'gradle-8.9/bin/gradle.bat'
if not gradle.exists():
    f=ROOT/'gradle.zip';checksum=get('https://services.gradle.org/distributions/gradle-8.9-bin.zip.sha256').decode().strip();fetch('https://services.gradle.org/distributions/gradle-8.9-bin.zip',f,checksum);unpack(f,ROOT)
env=os.environ.copy();env['JAVA_HOME']=str(java_home);env['ANDROID_HOME']=str(sdk);env['PATH']=str(java_home/'bin')+os.pathsep+env['PATH']
subprocess.run([str(manager),'--sdk_root='+str(sdk),'--licenses'],input='y\n'*100,text=True,env=env,stdout=subprocess.DEVNULL,check=True)
subprocess.run([str(manager),'--sdk_root='+str(sdk),'platform-tools','platforms;android-35','build-tools;35.0.0'],env=env,check=True,stdout=subprocess.DEVNULL)
print('Installing JADX and apktool',flush=True)
jar=ROOT/'apktool.jar'
if not jar.exists():
    url,digest=release('iBotPeaches/Apktool',lambda n:n.endswith('.jar'));fetch(url,jar,digest)
jadx=ROOT/'jadx'
if not (jadx/'lib').exists():
    url,digest=release('skylot/jadx',lambda n:n.startswith('jadx-') and n.endswith('.zip') and 'gui' not in n and 'with-jre' not in n)
    f=ROOT/'jadx.zip';fetch(url,f,digest);unpack(f,jadx)
settings={'JAVA_HOME':str(java_home),'ANDROID_HOME':str(sdk),'GRADLE_HOME':str(gradle.parent.parent),'APKTOOL_JAR':str(jar),'JADX_LIB_DIR':str(jadx/'lib')}
(ROOT/'environment.json').write_text(json.dumps(settings,indent=2))
print('Portable Android toolchain installed and SDK packages verified',flush=True)
