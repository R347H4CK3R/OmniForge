"""Read-only APK inspection and actual host Android project builds; no source equivalence claims."""
import hashlib,json,os,pathlib,shutil,subprocess,zipfile
MAX_BYTES=512*1024*1024

def artifact_info(path,root):
    p=pathlib.Path(path);digest=hashlib.sha256()
    with p.open('rb') as f:
        for block in iter(lambda:f.read(65536),b''):digest.update(block)
    return {'path':str(p.resolve().relative_to(pathlib.Path(root).resolve())),'sha256':digest.hexdigest(),'size':p.stat().st_size}

def inspect_apk(path):
    p=pathlib.Path(path)
    if p.stat().st_size>MAX_BYTES:raise ValueError('APK exceeds 512 MiB')
    with zipfile.ZipFile(p) as z:
        infos=z.infolist()
        if len(infos)>50000 or sum(i.file_size for i in infos)>2*1024**3:raise ValueError('Archive exceeds inspection budget')
        for i in infos:
            n=i.filename
            if '\\' in n or n.startswith('/') or ':' in n or '..' in pathlib.PurePosixPath(n).parts:raise ValueError('Unsafe archive entry')
        names=[i.filename for i in infos]
        if 'AndroidManifest.xml' not in names:raise ValueError('Not an APK: manifest missing')
        return {'schema':1,'sha256':artifact_info(p,p.parent)['sha256'],'entries':len(names),
          'dex_files':[n for n in names if n.endswith('.dex')],
          'abis':sorted({n.split('/')[1] for n in names if n.startswith('lib/') and len(n.split('/'))>2}),
          'files':names[:5000],'original_source_recovered':False,'signature_validated':False,
          'note':'ZIP inventory is not signature validation or proof of launch.'}

def build_project(folder,runner=subprocess.run):
    root=pathlib.Path(folder).resolve()
    if not any((root/x).is_file() for x in ('settings.gradle','settings.gradle.kts')):raise ValueError('Select an Android Gradle source project')
    gradle=shutil.which('gradle')
    if not gradle:return {'built':False,'error':'Install Gradle, JDK 17 and Android SDK on the host'}
    try:
        r=runner([gradle,'--no-daemon','assembleDebug'],cwd=root,capture_output=True,text=True,timeout=900,shell=False)
        apks=[str(p.relative_to(root)) for p in root.glob('**/build/outputs/apk/**/*.apk')]
        return {'built':r.returncode==0 and bool(apks),'exit_code':r.returncode,'apks':apks,'artifacts':[artifact_info(root/p,root) for p in apks],'log':(r.stdout+'\n'+r.stderr)[-24000:]}
    except (OSError,subprocess.TimeoutExpired) as e:return {'built':False,'error':str(e)[:500]}

def decompile_apk(path,out,runner=subprocess.run):
    inspect_apk(path)
    tool=shutil.which('jadx')
    command=[shutil.which('java') or 'java','-cp',str(pathlib.Path(os.environ['JADX_LIB_DIR'])/'*'),'jadx.cli.JadxCLI'] if os.environ.get('JADX_LIB_DIR') else ([tool] if tool else None)
    if not command:return {'decompiled':False,'error':'Install JADX on the host to inspect Java-like decompilation'}
    r=runner(command+['--no-imports','-d',str(out),str(path)],capture_output=True,text=True,timeout=900,shell=False)
    return {'decompiled':r.returncode==0,'output':str(out),'log':(r.stdout+r.stderr)[-12000:],'original_source_recovered':False}

if __name__=='__main__':
    import argparse
    a=argparse.ArgumentParser();a.add_argument('apk');a.add_argument('--output');args=a.parse_args()
    data=json.dumps(inspect_apk(args.apk),indent=2)
    if args.output:pathlib.Path(args.output).write_text(data)
    else:print(data)

def decode_resources(path,out,runner=subprocess.run):
    inspect_apk(path)
    tool=shutil.which('apktool')
    command=[shutil.which('java') or 'java','-jar',os.environ['APKTOOL_JAR']] if os.environ.get('APKTOOL_JAR') else ([tool] if tool else None)
    if not command:return {'decoded':False,'error':'Install apktool on the host for resource editing/rebuild'}
    r=runner(command+['d','-f','-o',str(out),str(path)],capture_output=True,text=True,timeout=900,shell=False)
    return {'decoded':r.returncode==0,'output':str(out),'log':(r.stdout+r.stderr)[-12000:],'original_source_recovered':False}

def rebuild_resources(folder,workspace,runner=subprocess.run):
    root=pathlib.Path(folder).resolve()
    if not (root/'apktool.yml').is_file():raise ValueError('Select an apktool decoded resource directory')
    tool=shutil.which('apktool')
    command=[shutil.which('java') or 'java','-jar',os.environ['APKTOOL_JAR']] if os.environ.get('APKTOOL_JAR') else ([tool] if tool else None)
    if not command:return {'built':False,'error':'Install apktool on the host'}
    out=root/'dist'/'rebuilt.apk'
    r=runner(command+['b',str(root),'-o',str(out)],capture_output=True,text=True,timeout=900,shell=False)
    result={'built':r.returncode==0 and out.is_file(),'signed':False,'log':(r.stdout+r.stderr)[-12000:]}
    keystore=os.environ.get('ANDROID_WORKBENCH_KEYSTORE');password_file=os.environ.get('ANDROID_WORKBENCH_PASSWORD_FILE');signer=shutil.which('apksigner')
    if result['built'] and keystore and password_file and signer:
        signed=root/'dist'/'rebuilt-signed.apk'
        s=runner([signer,'sign','--ks',keystore,'--ks-pass','file:'+password_file,'--out',str(signed),str(out)],capture_output=True,text=True,timeout=120,shell=False)
        if s.returncode==0:out=signed;result['signed']=True
        else:result['log']+='\nSigning failed: '+s.stderr[-2000:]
    result['artifacts']=[artifact_info(out,workspace)] if result['built'] else []
    result['note']='Resource/smali rebuild, not recovered original source. Modified apps need signing and device testing.'
    return result
