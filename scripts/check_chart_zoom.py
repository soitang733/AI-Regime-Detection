"""Exercise real Plotly zoom buttons and wheel zoom on desktop and mobile."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def main():
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe', headless=True)
        for width in [1440, 390]:
            page = browser.new_page(viewport={'width': width, 'height': 1000})
            page.goto('http://127.0.0.1:8501', wait_until='networkidle')
            page.locator('.foot').wait_for(timeout=60000)
            sidebar = page.get_by_test_id('stSidebar')

            def select(label):
                if sidebar.get_attribute('data-collapsed') == 'true':
                    page.get_by_test_id('stExpandSidebarButton').click()
                sidebar.get_by_text(label, exact=True).click()
                page.wait_for_timeout(400)
                page.wait_for_function("document.querySelector('[data-testid=stApp]').dataset.testScriptState === 'notRunning'")
                page.locator('.foot').wait_for()
                if width < 1000 and sidebar.get_attribute('data-collapsed') == 'false':
                    page.get_by_test_id('stSidebarCollapseButton').click()

            for asset in ['BTC', 'ETH']:
                select(asset)
                for name, count in [('2.  Regime History', 2), ('4.  Portfolio & Risk', 1)]:
                    select(name)
                    charts = page.locator('.js-plotly-plot:visible')
                    expect(charts).to_have_count(count, timeout=60000)
                    for index in range(count):
                        chart = charts.nth(index)
                        chart.scroll_into_view_if_needed()
                        page.wait_for_timeout(300)
                        initial = chart.evaluate("e => e._fullLayout.xaxis.range.slice()")
                        span = lambda: chart.evaluate("e => {const r=e._fullLayout.xaxis.range; return Date.parse(r[1])-Date.parse(r[0]);}")
                        before = span()
                        chart.locator('.modebar-btn[data-title="Zoom in"]').click()
                        page.wait_for_timeout(250)
                        zoomed = span()
                        assert zoomed < before * .95
                        chart.locator('.modebar-btn[data-title="Zoom out"]').click()
                        page.wait_for_timeout(250)
                        assert span() > zoomed * 1.05
                        chart.locator('.modebar-btn[data-title="Reset axes"]').click()
                        page.wait_for_timeout(250)
                        assert abs(span() / before - 1) < 1e-6
                        # Hover scrolls the actual subplot into view; a page-coordinate
                        # wheel can otherwise hit outside a tall mobile portfolio plot.
                        chart.locator('.nsewdrag').first.hover()
                        page.mouse.wheel(0, -200)
                        page.wait_for_timeout(300)
                        assert span() < before * .95
                        chart.locator('.modebar-btn[data-title="Reset axes"]').click()
                        page.wait_for_timeout(250)
                        assert abs(span() / before - 1) < 1e-6
                        assert not page.get_by_test_id('stException').count()
                        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                        result = {'asset': asset, 'page': name, 'chart_index': index, 'width': width,
                                  'zoom_in': True, 'zoom_out': True, 'wheel_zoom': True, 'reset': True,
                                  'initial_x_range': initial, 'passed': True}
                        results.append(result)
                        print(json.dumps(result), flush=True)
            page.close()
        browser.close()
    out = ROOT / 'outputs/research_v2/ui/chart_zoom.json'
    out.write_text(json.dumps({'checked_at_utc': datetime.now(timezone.utc).isoformat(), 'checks': results,
        'source_sha256': hashlib.sha256((ROOT / 'dashboard/v2_pages.py').read_bytes()).hexdigest(),
        'chart_modules_sha256':{p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
                               for p in [ROOT/'dashboard/app.py',ROOT/'dashboard/ui.py',*sorted((ROOT/'dashboard').glob('v2_*.py'))]}}, indent=2))


if __name__ == '__main__':
    main()
