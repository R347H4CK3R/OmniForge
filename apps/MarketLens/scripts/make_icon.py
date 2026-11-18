"""Render deterministic native icon from project-owned geometric artwork."""
from pathlib import Path
import json
from PIL import Image, ImageDraw
root=Path(__file__).resolve().parents[1]/'App/Assets.xcassets'
folder=root/'AppIcon.appiconset'; folder.mkdir(parents=True,exist_ok=True)
im=Image.new('RGB',(1024,1024),(9,15,24)); d=ImageDraw.Draw(im)
d.ellipse((180,135,810,765),outline=(86,217,199),width=45)
d.line((715,680,875,860),fill=(86,217,199),width=65)
d.line([(275,580),(390,440),(485,500),(600,320),(715,365)],fill=(235,244,248),width=34,joint='curve')
for x,y in [(275,580),(390,440),(485,500),(600,320),(715,365)]:d.ellipse((x-18,y-18,x+18,y+18),fill=(235,244,248))
im.save(folder/'AppIcon.png')
(folder/'Contents.json').write_text(json.dumps({'images':[{'filename':'AppIcon.png','idiom':'universal','platform':'ios','size':'1024x1024'}],'info':{'author':'xcode','version':1}},indent=2))
(root/'Contents.json').write_text(json.dumps({'info':{'author':'xcode','version':1}}))
