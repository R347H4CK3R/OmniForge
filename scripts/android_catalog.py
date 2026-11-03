"""Generate the Android APK source only from an existing verified release artifact."""
import hashlib,json,pathlib,urllib.parse

def catalog(apk,version,url):
    u=urllib.parse.urlsplit(url)
    if u.scheme!='https' or u.hostname!='github.com' or not u.path.startswith('/R347H4CK3R/OmniForge/releases/download/') or u.username:raise ValueError('Use this repository release HTTPS URL')
    if not isinstance(version,int) or version<=0:raise ValueError('Invalid version code')
    p=pathlib.Path(apk);digest=hashlib.sha256()
    with p.open('rb') as f:
        for block in iter(lambda:f.read(65536),b''):digest.update(block)
    return {'schema':1,'name':'OmniForge Android','applicationId':'com.r347h4ck3r.omniforge','versionCode':version,'versionName':f'1.0.{version}','minSdk':26,'downloadUrl':url,'sha256':digest.hexdigest(),'size':p.stat().st_size,'notes':'Android APK edition. Requires Android installation confirmation; private remote services need Tailscale.'}
if __name__=='__main__':
    import sys
    pathlib.Path(sys.argv[4]).write_text(json.dumps(catalog(sys.argv[1],int(sys.argv[2]),sys.argv[3]),indent=2)+'\n')
