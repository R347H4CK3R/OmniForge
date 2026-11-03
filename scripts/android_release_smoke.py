"""Exercise the actual signed release via ADB in an isolated CI emulator."""
import pathlib,re,subprocess,time,xml.etree.ElementTree as ET
OUT=pathlib.Path('release-verification');OUT.mkdir(exist_ok=True)
def adb(*args):return subprocess.check_output(['adb',*args],text=True,stderr=subprocess.STDOUT,timeout=45)
def tree():
    adb('shell','uiautomator','dump','/sdcard/omniforge-ui.xml')
    return ET.fromstring(adb('shell','cat','/sdcard/omniforge-ui.xml'))
def find(label,description=False):
    last=None
    for attempt in range(10):
        try:
            root=tree();node=next((n for n in root.iter('node') if n.get('content-desc' if description else 'text')==label),None)
            if node is not None:return node
        except (subprocess.SubprocessError,ET.ParseError) as e:last=e
        time.sleep(1)
    try:
        root=tree();(OUT/'failure-ui.xml').write_text(ET.tostring(root,encoding='unicode'))
        screenshot('failure')
        (OUT/'failure-logcat.txt').write_text(adb('logcat','-d','-t','300'))
    except Exception:pass
    raise AssertionError(f'UI element missing: {label}; {last}')
def bounds(node):return tuple(map(int,re.findall(r'\d+',node.get('bounds',''))))
def tap(node):
    x1,y1,x2,y2=bounds(node);adb('shell','input','tap',str((x1+x2)//2),str((y1+y2)//2))
def screenshot(name):
    with (OUT/(name+'.png')).open('wb') as f:subprocess.run(['adb','exec-out','screencap','-p'],stdout=f,check=True,timeout=20)
adb('uninstall','com.r347h4ck3r.omniforge') if 'package:com.r347h4ck3r.omniforge' in adb('shell','pm','list','packages') else None
print(adb('install','OmniForge-Android.apk'))
print(adb('shell','am','start','-W','-n','com.r347h4ck3r.omniforge/.MainActivity'))
find('OmniForge');screenshot('signed-release-home');tap(find('Remote'))
for mode in ('Open desktop','Open terminal'):
    tap(find(mode));find('Exit remote full screen',True)
    root=tree();web=next(n for n in root.iter('node') if n.get('class')=='android.webkit.WebView')
    x1,y1,x2,y2=bounds(web)
    assert x2-x1>y2-y1,'Remote release view did not rotate to landscape'
    screenshot(mode.replace(' ','_'))
    tap(find('Exit remote full screen',True));find('Open terminal')
print('PASS: signed APK installs, launches, and both remote modes open in landscape')
