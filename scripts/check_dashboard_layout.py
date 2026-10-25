"""Browser acceptance for real dashboard layout (requires running Streamlit and Playwright)."""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
PAGES = ["Overview", "Regime History", "Model Comparison", "Portfolio & Risk"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--executable", required=True)
    parser.add_argument("--url", default="http://127.0.0.1:8501")
    args = parser.parse_args()
    checks = []
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=args.executable, headless=True)
        for width, height in [(1920, 1080), (1366, 768), (1280, 800), (1024, 768), (390, 844)]:
            page = browser.new_page(viewport={"width": width, "height": height})
            page.goto(args.url, wait_until="networkidle")
            page.locator(".foot").wait_for(timeout=60000)
            sidebar = page.get_by_test_id("stSidebar")
            for asset in ["BTC", "ETH"]:
                for index, name in enumerate(PAGES, 1):
                    if sidebar.get_attribute("data-collapsed") == "true":
                        page.get_by_test_id("stExpandSidebarButton").click()
                    sidebar.get_by_text(asset, exact=True).click()
                    page.wait_for_timeout(200)
                    page.wait_for_function("document.querySelector('[data-testid=stApp]').dataset.testScriptState === 'notRunning'")
                    sidebar.get_by_text(f"{index}.  {name}", exact=True).click()
                    page.wait_for_timeout(300)
                    page.wait_for_function("document.querySelector('[data-testid=stApp]').dataset.testScriptState === 'notRunning'", timeout=60000)
                    page.locator(".foot").wait_for()
                    if name == "Overview":
                        page.locator('.st-key-card_ai_radar').wait_for()
                    elif name == "Regime History":
                        page.locator('.st-key-card_controls').wait_for()
                    elif name == "Portfolio & Risk":
                        page.get_by_text('NAV cuối (regime-aware)', exact=True).wait_for()
                    else:
                        page.locator('.kpi-grid').wait_for()
                    if width < 768 and sidebar.get_attribute("data-collapsed") == "false":
                        page.get_by_test_id("stSidebarCollapseButton").click()
                        page.wait_for_timeout(350)
                    measured = page.evaluate("""() => {
                      const main = document.querySelector('[data-testid="stMain"]');
                      const cards = [...document.querySelectorAll('.kpi')];
                      return {
                        main_width: main.clientWidth, main_scroll_width: main.scrollWidth,
                        kpi_count: cards.length,
                        clipped_kpi: cards.flatMap((c,i) => [...c.querySelectorAll('.l,.v,.s')]
                          .filter(e => e.scrollWidth > e.clientWidth + 1 || e.scrollHeight > e.clientHeight + 1)
                          .map(e => ({card:i, text:e.innerText}))),
                        exceptions: [...document.querySelectorAll('[data-testid="stException"]')].map(e=>e.innerText)
                      };
                    }""")
                    measured.update(width=width, height=height, asset=asset, page=name)
                    measured["passed"] = ((name == "Regime History" or measured["kpi_count"] > 0)
                                          and not measured["exceptions"] and not measured["clipped_kpi"]
                                          and measured["main_scroll_width"] <= measured["main_width"] + 1)
                    checks.append(measured)
                    if asset == "BTC" and name == "Overview":
                        page.screenshot(path=str(ROOT / f"outputs/figures/layout_{width}.png"))
            page.close()
        browser.close()
    result = {"checked_at_utc": datetime.now(timezone.utc).isoformat(),
              "status": "passed" if all(c["passed"] for c in checks) else "failed", "checks": checks}
    (ROOT / "outputs/metadata/ui_layout_acceptance.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    raise SystemExit(0 if result["status"] == "passed" else 1)


if __name__ == "__main__":
    main()
