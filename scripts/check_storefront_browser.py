"""Browser smoke test and review screenshots, run by catalog-storefront.yml."""
from pathlib import Path
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser=p.chromium.launch()
    page=browser.new_page(viewport={'width':1440,'height':1100})
    errors=[]
    page.on('pageerror',lambda error: errors.append(str(error)))
    page.goto(Path('catalog/index.html').resolve().as_uri())
    count=page.locator('article.app').count()
    assert count>0
    page.locator('#search').fill('VoiceMatrix')
    assert page.locator('article.app:visible').count()==1
    page.locator('#search').fill('no-matching-app-123')
    assert page.locator('#empty').is_visible()
    page.locator('#search').fill('')
    page.locator('#category').select_option(label='Games')
    assert page.locator('article.app:visible').count()>0
    assert all(category=='Games' for category in page.locator('article.app:visible').evaluate_all('(els)=>els.map(e=>e.dataset.category)'))
    page.locator('#category').select_option('')
    assert page.locator('article.app:visible').count()==count
    # Use the exact checked-in genuine captures to avoid remote-image availability affecting QA.
    page.route('https://raw.githubusercontent.com/R347H4CK3R/OmniForge/main/catalog/screenshots/*',lambda route: route.fulfill(path=Path('catalog/screenshots')/route.request.url.rsplit('/',1)[-1]))
    page.reload()
    page.locator('.gallery img').evaluate_all('(imgs)=>imgs.forEach(i=>i.loading="eager")')
    page.wait_for_function('Array.from(document.querySelectorAll(".gallery img")).every(i=>i.complete&&i.naturalWidth>0)')
    Path('storefront-preview').mkdir(exist_ok=True)
    page.screenshot(path='storefront-preview/desktop.png',full_page=True)
    page.set_viewport_size({'width':390,'height':844})
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    page.screenshot(path='storefront-preview/mobile.png',full_page=True)
    assert not errors,errors
    browser.close()
print('PASS: search, categories, empty state, screenshots, mobile overflow, JavaScript errors')
