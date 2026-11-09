"""Accessible static storefront; reads catalog data without modifying installer metadata."""
import html
import json
from pathlib import Path

SOURCE_URL = 'https://raw.githubusercontent.com/R347H4CK3R/OmniForge/main/unified-source.json'

def render_storefront(source):
    e=lambda value: html.escape(str(value), quote=True)
    cards=[]
    for app in source['apps']:
        v=app['versions'][0]
        category=app.get('category','apps').title()
        previews=''.join(f'<a href="{e(s["imageURL"])}" target="_blank" rel="noopener"><img loading="lazy" src="{e(s["imageURL"])}" alt="{e(app["name"])} reviewed simulator screenshot {i+1}"></a>' for i,s in enumerate(app.get('screenshots',[])))
        gallery=f'<div class="gallery">{previews}</div><p class="caption">Reviewed simulator previews · Tap to view full size. Development UI may differ from the current release. Not proof of device behavior.</p>' if previews else '<div class="missing"><span aria-hidden="true">▧</span><strong>Preview coming soon</strong><small>No reviewed screenshot available yet.</small></div>'
        cards.append(f'''<article class="app" data-category="{e(category)}" data-search="{e((app['name']+' '+app.get('subtitle','')+' '+category).lower())}">
<header class="app-head"><img class="icon" src="{e(app['iconURL'])}" alt=""><div><span class="category">{e(category)}</span><h2>{e(app['name'])}</h2><p>{e(app.get('subtitle',''))}</p></div></header>
{gallery}
<div class="meta"><span><strong>{e(v['version'])}</strong>Version · build {e(v['buildVersion'])}</span><span><strong>iOS {e(v['minOSVersion'])}+</strong>Requires</span><span><strong>{v['size']/1_000_000:.2f} MB</strong>Download</span></div>
<p class="description">{e(app.get('localizedDescription',''))}</p>
<div class="card-bottom"><a class="get" href="{e(v['downloadURL'])}">Get IPA <span aria-hidden="true">↗</span></a><span>Signing or compatible container required</span></div>
<details><summary>Release notes &amp; app details</summary><p>{e(v.get('localizedDescription',''))}</p><p class="bundle">Bundle ID: {e(app['bundleIdentifier'])}</p></details></article>''')
    categories=sorted({a.get('category','apps').title() for a in source['apps']})
    options=''.join(f'<option>{e(c)}</option>' for c in categories)
    template=Path(__file__).with_name('storefront.html').read_text()
    return template.replace('{{CARDS}}','\n'.join(cards)).replace('{{COUNT}}',str(len(cards))).replace('{{OPTIONS}}',options).replace('{{SOURCE}}',SOURCE_URL)

if __name__=='__main__':
    Path('catalog/index.html').write_text(render_storefront(json.loads(Path('unified-source.json').read_text())))
