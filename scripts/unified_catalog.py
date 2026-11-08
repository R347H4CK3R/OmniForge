#!/usr/bin/env python3
"""Aggregate explicitly approved public IPA feeds, retaining last-good entries.

No credentials are sent: every feed, release and binary must be public.
Downloaded apps are inspected as ZIP data, never executed or extracted.
"""
import argparse
import copy
import hashlib
import json
import os
import plistlib
import re
import struct
import tempfile
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

MAX_IPA = 1_500_000_000


def numeric(value):
    if not re.fullmatch(r'\d+(?:\.\d+)*', str(value)):
        raise ValueError('non-numeric app version requires manual review')
    parts = [int(x) for x in str(value).split('.')]
    while len(parts)>1 and parts[-1]==0: parts.pop()
    return tuple(parts)


def version_key(app):
    v = app['versions'][0]
    return numeric(v['version']), numeric(v['buildVersion'])


def inspect_ipa(path, bundle_id):
    with zipfile.ZipFile(path) as z:
        names = [n for n in z.namelist() if re.fullmatch(r'Payload/[^/]+\.app/Info\.plist', n)]
        if len(names) != 1: raise ValueError('expected exactly one top-level app')
        member = z.getinfo(names[0])
        if member.file_size > 1_000_000: raise ValueError('oversized Info.plist')
        info = plistlib.loads(z.read(member))
        if info.get('CFBundleIdentifier') != bundle_id: raise ValueError('bundle identity mismatch')
        executable = info.get('CFBundleExecutable', '')
        if not executable or '/' in executable or executable in ('.','..'): raise ValueError('invalid executable')
        try: binary = z.getinfo(names[0].rsplit('/',1)[0]+'/'+executable)
        except KeyError as exc: raise ValueError('missing executable') from exc
        if binary.file_size < 32: raise ValueError('missing executable data')
        platforms=info.get('CFBundleSupportedPlatforms', ['iPhoneOS'])
        if platforms != ['iPhoneOS'] or info.get('DTPlatformName','iphoneos')!='iphoneos':
            raise ValueError('IPA is not an iOS device build')
        with z.open(binary) as f:
            header=f.read(32); magic=header[:4]; offset=0
            if magic in (b'\xca\xfe\xba\xbe',b'\xbe\xba\xfe\xca'):
                order='big' if magic==b'\xca\xfe\xba\xbe' else 'little'
                count=int.from_bytes(header[4:8],order)
                if not 0<count<=32: raise ValueError('invalid fat Mach-O')
                f.seek(8); entries=f.read(count*20)
                candidates=[int.from_bytes(entries[i*20+8:i*20+12],order) for i in range(count)
                            if int.from_bytes(entries[i*20:i*20+4],order)==0x0100000c]
                if len(candidates)!=1: raise ValueError('expected one ARM64 Mach-O slice')
                offset=candidates[0]; f.seek(offset); header=f.read(32); magic=header[:4]
            if magic not in (b'\xcf\xfa\xed\xfe',b'\xfe\xed\xfa\xcf'): raise ValueError('invalid Mach-O')
            endian='<' if magic==b'\xcf\xfa\xed\xfe' else '>'
            fields=struct.unpack(endian+'8I',header)
            if fields[1]!=0x0100000c or fields[3]!=2: raise ValueError('expected ARM64 executable')
            count,size=fields[4:6]
            if not 0<count<=4096 or not 0<size<=2_000_000 or offset+32+size>binary.file_size:
                raise ValueError('invalid Mach-O commands')
            commands=f.read(size); pos=0; ios=False
            for _ in range(count):
                if pos+8>len(commands): raise ValueError('truncated load command')
                cmd,length=struct.unpack_from(endian+'2I',commands,pos)
                if length<8 or pos+length>len(commands): raise ValueError('invalid load command')
                if cmd==0x32:
                    if length<24 or struct.unpack_from(endian+'I',commands,pos+8)[0]!=2:
                        raise ValueError('Mach-O is not an iOS device build')
                    ios=True
                elif cmd==0x25: ios=True
                elif cmd in (0x24,0x2f,0x30): raise ValueError('non-iOS Mach-O platform')
                pos+=length
            if not ios: raise ValueError('missing iOS device platform command')
        version = str(info['CFBundleShortVersionString']); build = str(info['CFBundleVersion'])
        numeric(version); numeric(build)
        minimum = str(info['MinimumOSVersion']); numeric(minimum)
        return {'version':version,'buildVersion':build,'minOSVersion':minimum}


def release_coordinates(url, repository):
    u = urllib.parse.urlsplit(url)
    prefix = '/'+repository+'/releases/download/'
    if u.scheme != 'https' or u.netloc != 'github.com' or u.query or u.fragment or not u.path.startswith(prefix):
        raise ValueError('download must be an immutable release URL in the approved repository')
    bits = u.path[len(prefix):].split('/')
    if len(bits)!=2 or not all(bits) or not bits[1].lower().endswith('.ipa'): raise ValueError('invalid IPA release URL')
    return tuple(urllib.parse.unquote(x) for x in bits)


def verify_release(release, url, size, allow_prerelease):
    if release.get('draft') or (release.get('prerelease') and not allow_prerelease): raise ValueError('unapproved release channel')
    assets=[a for a in release.get('assets',[]) if a.get('browser_download_url')==url and a.get('state')=='uploaded']
    if len(assets)!=1 or assets[0]['size']!=size or not 0<size<=MAX_IPA: raise ValueError('missing or mismatched release asset')
    return assets[0]


def public_json(url):
    req = urllib.request.Request(url, headers={'User-Agent':'verified-app-catalog','Accept':'application/vnd.github+json'})
    with urllib.request.urlopen(req, timeout=60) as response:
        raw=response.read(10_000_001)
    if len(raw)>10_000_000: raise ValueError('oversized JSON')
    return json.loads(raw)


def download(url, path, size):
    req=urllib.request.Request(url,headers={'User-Agent':'verified-app-catalog'})
    digest=hashlib.sha256(); count=0
    with urllib.request.urlopen(req,timeout=180) as response, open(path,'wb') as out:
        while True:
            data=response.read(1024*1024)
            if not data: break
            count+=len(data)
            if count>size or count>MAX_IPA: raise ValueError('oversized IPA')
            out.write(data); digest.update(data)
    if count!=size: raise ValueError('IPA byte count mismatch')
    return digest.hexdigest()


def verify_character_evidence(proof, bid, actual, sha, size):
    inspection=proof.get('inspection', {})
    if (proof.get('nativeDiagnosticSpeechPassed') is not True
        or proof.get('nativeSimulatorConversionPassed') is not True
        or inspection.get('archive')!='passed'
        or inspection.get('bundleIdentifier')!=bid
        or str(inspection.get('version'))!=actual['version']
        or str(inspection.get('build'))!=actual['buildVersion']
        or proof.get('ipaSHA256')!=sha or proof.get('ipaBytes')!=size):
        raise ValueError('character release evidence did not verify this IPA')


def public_app_metadata(source, repo):
    allowed=('name','bundleIdentifier','developerName','subtitle','localizedDescription','iconURL','tintColor','category')
    app={key:copy.deepcopy(source[key]) for key in allowed if key in source}
    url=urllib.parse.urlsplit(app.get('iconURL',''))
    if url.scheme!='https' or url.query or url.fragment or not (
        url.netloc=='raw.githubusercontent.com' and url.path.startswith('/'+repo+'/')
        or url.netloc=='github.com' and url.path.startswith('/'+repo+'/releases/download/')):
        raise ValueError('icon must be public media in the approved repository')
    return app


def load_app(entry):
    repo=entry['repository']; bid=entry['bundleIdentifier']
    print(f'Checking {repo}: public source and approved release', flush=True)
    # An unauthenticated read is intentional: private repositories cannot enter a public catalog.
    meta=public_json('https://api.github.com/repos/'+repo)
    if meta.get('private') or meta.get('visibility','public')!='public': raise ValueError('repository is not public')
    feed=public_json(entry['sourceURL'])
    apps=[a for a in feed.get('apps',[]) if a.get('bundleIdentifier')==bid]
    if len(apps)!=1: raise ValueError('missing or duplicate source app')
    app=public_app_metadata(apps[0],repo); candidate=apps[0]['versions'][0]
    url=candidate['downloadURL']; tag,_=release_coordinates(url,repo)
    if not re.fullmatch(entry['tagPattern'],tag): raise ValueError('release tag outside approved channel')
    release=public_json('https://api.github.com/repos/'+repo+'/releases/tags/'+urllib.parse.quote(tag,safe=''))
    if release.get('tag_name')!=tag: raise ValueError('release tag mismatch')
    asset=verify_release(release,url,candidate['size'],entry.get('allowPrerelease',False))
    names={a['name']:a for a in release['assets']}
    for name in entry.get('requiredEvidenceAssets',[]):
        if name not in names or names[name].get('state')!='uploaded' or not names[name]['size']:
            raise ValueError('required release evidence missing: '+name)
    with tempfile.TemporaryDirectory(prefix='catalog-') as tmp:
        print(f'Inspecting {repo} {tag}: downloading {asset["size"]} bytes', flush=True)
        path=Path(tmp)/'app.ipa'; sha=download(url,path,asset['size'])
        if asset.get('digest') and asset['digest']!='sha256:'+sha: raise ValueError('release SHA-256 mismatch')
        actual=inspect_ipa(path,bid)
    if entry.get('evidencePolicy')=='character':
        proof=public_json(names['character-release-verification.json']['browser_download_url'])
        verify_character_evidence(proof,bid,actual,sha,asset['size'])
    current={'date':release['published_at'],'downloadURL':url,'size':asset['size'],**actual}
    current['localizedDescription']=candidate.get('localizedDescription',app.get('localizedDescription',''))
    # Only the newly inspected version is emitted. Do not copy uninspected historical entries.
    app['versions']=[current]
    app.update({'version':actual['version'],'versionDate':current['date'],'downloadURL':url,'size':asset['size']})
    for key in ('name','subtitle','localizedDescription','category','screenshots'):
        if key in entry: app[key]=entry[key]
    app['_verification']={'sha256':sha,'release':release['html_url'],'assetId':asset['id'],'level':'IPA structure and published release metadata; physical device behavior not certified'}
    print(f'Verified {repo}: {actual["version"]} build {actual["buildVersion"]}; SHA-256 {sha}', flush=True)
    return app


def refresh(previous, registry, loader=load_app):
    identifiers=[e['bundleIdentifier'] for e in registry]
    if len(set(identifiers))!=len(identifiers): raise ValueError('duplicate registry bundle identifiers')
    old={a['bundleIdentifier']:a for a in previous.get('apps',[])}
    if len(old)!=len(previous.get('apps',[])): raise ValueError('duplicate previous app identifiers')
    result=copy.deepcopy(previous); result['apps']=[]; errors=[]
    for entry in registry:
        bid=entry['bundleIdentifier']; prior=old.get(bid)
        try:
            app=loader(entry)
            if app.get('bundleIdentifier')!=bid: raise ValueError('loader identity mismatch')
            if prior and version_key(app)<version_key(prior): raise ValueError('refusing version rollback')
            if prior and version_key(app)==version_key(prior):
                before=prior['versions'][0].get('downloadURL'); after=app['versions'][0].get('downloadURL')
                if before and before!=after: raise ValueError('same version points to different asset')
                if prior.get('_verification',{}).get('sha256') and prior['_verification']['sha256']!=app.get('_verification',{}).get('sha256'):
                    raise ValueError('same version binary changed')
            result['apps'].append(app)
        except Exception as exc:
            errors.append({'bundleIdentifier':bid,'reason':str(exc)})
            print(f'Skipping {bid}: {exc}; retaining previous entry if available', flush=True)
            if prior: result['apps'].append(prior)
    return result,errors


def main():
    p=argparse.ArgumentParser(); p.add_argument('--registry',default='catalog/registry.json'); p.add_argument('--output',default='unified-source.json'); p.add_argument('--report',default='catalog-refresh-report.json'); args=p.parse_args()
    path=Path(args.output); state=Path('catalog/verified-state.json')
    previous=json.loads((state if state.exists() else path).read_text()); registry=json.loads(Path(args.registry).read_text())
    result,errors=refresh(previous,registry)
    # Keep verification metadata in a separate report, not in the AltStore app schema.
    state_temp=state.with_suffix('.tmp'); state_temp.write_text(json.dumps(result,indent=2)+'\n'); os.replace(state_temp,state)
    public=copy.deepcopy(result)
    for app in public['apps']: app.pop('_verification',None)
    serialized=json.dumps(public,indent=2)+'\n'
    temp=path.with_suffix(path.suffix+'.tmp'); temp.write_text(serialized); os.replace(temp,path)
    Path(args.report).write_text(json.dumps({'complete':True,'errors':errors,'apps':[{'bundleIdentifier':a['bundleIdentifier'],'verification':a.get('_verification')} for a in result['apps']]},indent=2)+'\n')
    print(json.dumps({'apps':len(result['apps']),'errors':errors}))
    if errors: raise SystemExit(1)

if __name__=='__main__': main()
