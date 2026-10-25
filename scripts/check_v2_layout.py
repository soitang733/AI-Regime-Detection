"""48 browser checks of the sole current dashboard, including no legacy selector."""
import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'outputs/research_v2/ui'
PAGES = ['Overview', 'Regime History', 'Model Comparison', 'Portfolio & Risk']
PAGE_LABELS = {'Overview':'Tổng quan', 'Regime History':'Lịch sử regime',
               'Model Comparison':'So sánh mô hình', 'Portfolio & Risk':'Danh mục và rủi ro'}
CASES = [(390, 1), (768, 1), (1280, 1), (1440, 1), (1920, 1), (1280, 1.25)]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    source_paths = ['dashboard/app.py', 'dashboard/ui.py'] + sorted(
        p.relative_to(ROOT).as_posix() for p in (ROOT/'dashboard').glob('v2_*.py'))
    source_hashes = {name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in source_paths}
    expected = {a: json.loads((ROOT/f'outputs/research_v2/m2/{a.lower()}_metadata.json').read_text())
                for a in ['BTC', 'ETH']}
    checks = []
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe', headless=True)
        for width, zoom in CASES:
            context = browser.new_context(viewport={'width': round(width/zoom), 'height': round(1000/zoom)},
                                          device_scale_factor=zoom)
            page = context.new_page()
            page.goto('http://127.0.0.1:8501', wait_until='networkidle')
            page.locator('.foot').wait_for(timeout=60000)
            sidebar = page.get_by_test_id('stSidebar')

            def select(text):
                if sidebar.get_attribute('data-collapsed') == 'true':
                    page.get_by_test_id('stExpandSidebarButton').click()
                    page.wait_for_timeout(350)
                sidebar.get_by_text(text, exact=True).click()
                page.wait_for_timeout(150)
                page.wait_for_function("document.querySelector('[data-testid=stApp]').dataset.testScriptState === 'notRunning'", timeout=60000)
                page.locator('.foot').wait_for(timeout=60000)

            for version in ['current']:
                for asset in ['BTC', 'ETH']:
                    select(asset)
                    for index, name in enumerate(PAGES, 1):
                        select(f'{index}.  {name}')
                        page.wait_for_function("""expected => {
                            const text=document.querySelector('.hero')?.innerText.trim();
                            return text && text.startsWith(expected.asset) && text.includes(expected.title);
                        }""", arg={'asset':asset,'title':PAGE_LABELS[name]}, timeout=60000)
                        page.wait_for_function("document.querySelector('[data-testid=stApp]').dataset.testScriptState === 'notRunning'", timeout=60000)
                        sidebar_text = sidebar.inner_text()
                        version_attribute = sidebar.locator('.asof').get_attribute('data-result-set')
                        main_hero = page.locator('.hero').inner_text()
                        sidebar_layout = sidebar.evaluate('(e) => ({sidebar_width:e.clientWidth,sidebar_scroll_width:e.scrollWidth})')
                        k = expected[asset]['K']
                        no_legacy = page.locator('.st-key-result_version').count() == 0 and 'PHIÊN KẾT QUẢ' not in sidebar_text
                        semantics = (f'Gaussian HMM · K = {k}' in sidebar_text and no_legacy
                                     and version_attribute == version and asset in main_hero
                                     and 'cập nhật mỗi ngày' not in sidebar_text and f'K={k}' in main_hero)
                        if name == 'Overview':
                            row_count = page.locator('.st-key-card_ai_radar table.cmp').first.locator('tr:has(td)').count()
                            semantics = semantics and row_count == k
                            if page.evaluate('innerWidth') <= 520:
                                semantics = semantics and page.locator('.regime-mobile-state:visible').count() == k
                        if page.evaluate('innerWidth') < 1000 and sidebar.get_attribute('data-collapsed') == 'false':
                            page.get_by_test_id('stSidebarCollapseButton').click()
                            page.wait_for_timeout(300)
                        measured = page.evaluate("""() => {
                          const main=document.querySelector('[data-testid=stMain]');
                          const side=document.querySelector('[data-testid=stSidebar]');
                          return {inner_width:innerWidth,dpr:devicePixelRatio,main_width:main.clientWidth,main_scroll_width:main.scrollWidth,
                            sidebar_width:side.clientWidth,sidebar_scroll_width:side.scrollWidth,
                            exceptions:[...document.querySelectorAll('[data-testid=stException]')].map(e=>e.innerText),
                            errors:[...document.querySelectorAll('[data-testid=stAlertContentError]')].map(e=>e.innerText),
                            kpi_count:document.querySelectorAll('.kpi').length,
                            clipped:[...document.querySelectorAll('.kpi .l,.kpi .v,.kpi .s')].filter(e=>e.scrollWidth>e.clientWidth+1||e.scrollHeight>e.clientHeight+1).map(e=>e.innerText)};
                        }""")
                        measured.update(asset=asset, page=name, version=version, width=width, zoom=zoom,
                                        expected_K=k, semantic_match=bool(semantics), legacy_selector_absent=no_legacy,
                                        checked_at_utc=datetime.now(timezone.utc).isoformat(),
                                        zoom_method='viewport/device-scale emulation' if zoom != 1 else 'unzoomed')
                        measured.update(sidebar_layout)
                        measured['passed'] = bool(semantics and not measured['exceptions'] and not measured['errors']
                            and not measured['clipped'] and measured['main_scroll_width'] <= measured['main_width']+1
                            and measured['sidebar_scroll_width'] <= measured['sidebar_width']+1
                            and abs(measured['inner_width']-width/zoom) <= 1 and abs(measured['dpr']-zoom) < .02
                            and (name not in ['Overview', 'Portfolio & Risk'] or measured['kpi_count'] > 0))
                        checks.append(measured)
                        print(json.dumps(measured, ensure_ascii=True), flush=True)
                        if asset == 'BTC' and name == 'Overview':
                            page.evaluate("document.querySelector('[data-testid=stMain]').scrollTop=0")
                            page.screenshot(path=str(OUT/f'{version}_overview_{width}_{zoom}.png'))
            context.close()
        browser.close()
    unchanged = all(hashlib.sha256((ROOT/name).read_bytes()).hexdigest() == digest for name, digest in source_hashes.items())
    passed = len(checks) == 48 and all(row['passed'] for row in checks) and unchanged
    (OUT/'acceptance.json').write_text(json.dumps({'status': 'passed' if passed else 'failed',
        'source_unchanged_during_check': unchanged, 'source_sha256': source_hashes, 'checks': checks}, indent=2))
    raise SystemExit(0 if passed else 1)


if __name__ == '__main__':
    main()
