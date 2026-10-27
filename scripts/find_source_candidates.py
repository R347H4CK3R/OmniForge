#!/usr/bin/env python3
"""Evidence-scored public source discovery for user-authorized IPA analysis.
Candidate matches are never labeled original source without explicit provenance."""
import json,os,sys,urllib.parse,urllib.request,pathlib
inp=pathlib.Path(sys.argv[1]); output=pathlib.Path(sys.argv[2]);output.mkdir(parents=True,exist_ok=True)
data=json.loads(inp.read_text())
bundle=str(data.get("app") or data.get("bundle_identifier") or "")
name=str(data.get("app_name") or bundle.split(".")[-1] or "")
queries=list(dict.fromkeys([name,bundle]))
headers={"Accept":"application/vnd.github+json","User-Agent":"OmniForge-source-discovery"}
if os.environ.get("GH_TOKEN"):headers["Authorization"]="Bearer "+os.environ["GH_TOKEN"]
result=[]
for q in queries[:2]:
 if not q:continue
 url="https://api.github.com/search/repositories?"+urllib.parse.urlencode({"q":q+" in:name,description,readme","per_page":10})
 try:
  req=urllib.request.Request(url,headers=headers)
  with urllib.request.urlopen(req,timeout=20) as response: listing=json.load(response)
  for repo in listing.get("items",[]):
   if repo.get("archived"):continue
   title=repo.get("full_name","")
   score=int(bundle.lower() in (repo.get("description") or "").lower())*3+int(name.lower() in title.lower())*2
   result.append({"repository":title,"url":repo.get("html_url"),"license":(repo.get("license") or {}).get("spdx_id"),
                  "score":score,"verified_original_source":False,"reason":"Search match only; provenance unverified"})
 except Exception as exc:
  result.append({"query":q,"error":str(exc)[:250]})
result.sort(key=lambda i:i.get("score",0),reverse=True)
(output/"source_candidates.json").write_text(json.dumps(result[:20],indent=2))
print("Candidate repositories:",len(result),"; none verified as original source")
