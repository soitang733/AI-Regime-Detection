"""Before/after screenshots of the same assets/pages at desktop and mobile sizes."""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
PAGES={'Overview':'Tổng quan','Regime History':'Lịch sử regime',
       'Model Comparison':'So sánh mô hình','Portfolio & Risk':'Danh mục và rủi ro'}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--phase',choices=['before','after'],required=True)
    args=parser.parse_args();out=ROOT/'reports/terminal_design'/args.phase;out.mkdir(parents=True,exist_ok=True)
    source={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (ROOT/'dashboard').glob('*.py')}
    records=[]
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe',headless=True)
        for width in [1440,390]:
            page=browser.new_page(viewport={'width':width,'height':1000})
            page.goto('http://127.0.0.1:8501',wait_until='networkidle');page.locator('.foot').wait_for(timeout=60000)
            side=page.get_by_test_id('stSidebar')
            def select(label):
                if side.get_attribute('data-collapsed')=='true':page.get_by_test_id('stExpandSidebarButton').click()
                side.get_by_text(label,exact=True).click();page.wait_for_timeout(350)
            for asset in ['BTC','ETH']:
                select(asset)
                for index,(name,title) in enumerate(PAGES.items(),1):
                    select(f'{index}.  {name}')
                    page.wait_for_function("v=>{const h=document.querySelector('.hero')?.innerText;return h&&h.trim().startsWith(v.asset)&&h.includes(v.title)}",
                                           arg={'asset':asset,'title':title},timeout=60000)
                    page.wait_for_function("document.querySelector('[data-testid=stApp]').dataset.testScriptState==='notRunning'",timeout=60000)
                    if width<1000 and side.get_attribute('data-collapsed')=='false':page.get_by_test_id('stSidebarCollapseButton').click()
                    page.evaluate("document.querySelector('[data-testid=stMain]').scrollTop=0")
                    page.wait_for_timeout(200)
                    filename=f'{asset}_{index}_{width}.png';page.screenshot(path=str(out/filename),full_page=True)
                    records.append({'asset':asset,'page':name,'width':width,'screenshot':filename,
                                    'errors':page.get_by_test_id('stException').count()})
            page.close()
        browser.close()
    (out/'manifest.json').write_text(json.dumps({'phase':args.phase,'captured_at_utc':datetime.now(timezone.utc).isoformat(),
        'source_sha256':source,'screenshots':records},indent=2))
    print(json.dumps({'phase':args.phase,'screenshots':len(records)}))


if __name__=='__main__':main()
