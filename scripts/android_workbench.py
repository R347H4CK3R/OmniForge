"""Read-only APK inspection and actual host Android project builds; no source equivalence claims."""
import hashlib,json,os,pathlib,shutil,subprocess,zipfile
MAX_BYTES=512*1024*1024

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
        return {'schema':1,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'entries':len(names),
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
        return {'built':r.returncode==0 and bool(apks),'exit_code':r.returncode,'apks':apks,'log':(r.stdout+'\n'+r.stderr)[-24000:]}
    except (OSError,subprocess.TimeoutExpired) as e:return {'built':False,'error':str(e)[:500]}

def decompile_apk(path,out,runner=subprocess.run):
    inspect_apk(path)
    tool=shutil.which('jadx')
    if not tool:return {'decompiled':False,'error':'Install JADX on the host to inspect Java-like decompilation'}
    r=runner([tool,'--no-imports','-d',str(out),str(path)],capture_output=True,text=True,timeout=900,shell=False)
    return {'decompiled':r.returncode==0,'output':str(out),'log':(r.stdout+r.stderr)[-12000:],'original_source_recovered':False}

if __name__=='__main__':
    import argparse
    a=argparse.ArgumentParser();a.add_argument('apk');a.add_argument('--output');args=a.parse_args()
    data=json.dumps(inspect_apk(args.apk),indent=2)
    if args.output:pathlib.Path(args.output).write_text(data)
    else:print(data)
