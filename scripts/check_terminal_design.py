"""Real browser acceptance of terminal filters, research tabs and downloads."""
import hashlib
import json
import pandas as pd
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'reports/terminal_design'


def main():
    expect.set_options(timeout=60000)
    sources=[ROOT/'dashboard/app.py',ROOT/'dashboard/ui.py',*sorted((ROOT/'dashboard').glob('v2_*.py'))]
    hashes={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    records=[]
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe',headless=True)
        for width in [1440,390]:
            page=browser.new_page(viewport={'width':width,'height':1000},accept_downloads=True)
            page.goto('http://127.0.0.1:8501',wait_until='networkidle')
            page.locator('.foot').wait_for(timeout=60000)
            sidebar=page.get_by_test_id('stSidebar')

            def settled():
                page.wait_for_timeout(350)
                page.wait_for_function("document.querySelector('[data-testid=stApp]').dataset.testScriptState==='notRunning'",timeout=60000)

            def navigate(name):
                if sidebar.get_attribute('data-collapsed')=='true':page.get_by_test_id('stExpandSidebarButton').click()
                sidebar.get_by_text(name,exact=True).click();settled()
                title={'1.  Overview':'Tổng quan','2.  Regime History':'Lịch sử regime',
                       '3.  Model Comparison':'So sánh mô hình','4.  Portfolio & Risk':'Danh mục và rủi ro'}[name]
                page.wait_for_function("v=>document.querySelector('.hero')?.innerText.includes(v)",arg=title,timeout=60000)
                settled()
                if width<1000 and sidebar.get_attribute('data-collapsed')=='false':page.get_by_test_id('stSidebarCollapseButton').click()

            def choose(label,value):
                box=page.get_by_test_id('stSelectbox').filter(has=page.get_by_text(label,exact=True))
                box.scroll_into_view_if_needed()
                page.wait_for_timeout(200)
                box.get_by_role('combobox').click()
                try:
                    page.get_by_role('option',name=value,exact=True).click()
                except Exception:
                    print(json.dumps({'selector_failure':label,'value':value,'width':width,
                                      'visible_options':page.get_by_role('option').all_text_contents()}),flush=True)
                    page.screenshot(path=str(OUT/'selector_failure.png'))
                    raise
                settled()

            def check(asset,section):
                expect(page.locator('.interpretation-section')).to_have_count(0)
                assert not page.get_by_test_id('stException').count()
                assert not page.get_by_test_id('stAlertContentError').count()
                assert page.get_by_test_id('stMain').evaluate('e=>e.scrollWidth<=e.clientWidth+1')
                assert page.locator('.st-key-result_version').count()==0
                records.append({'asset':asset,'width':width,'section':section,'passed':True})
                print(json.dumps(records[-1]),flush=True)

            for asset in ['BTC','ETH']:
                navigate('1.  Overview')
                page.locator('.st-key-top_asset').get_by_text(asset,exact=True).click();settled()
                page.wait_for_function("a=>document.querySelector('.hero')?.innerText.trim().startsWith(a)",arg=asset)
                meta=json.loads((ROOT/f'outputs/research_v2/m2/{asset.lower()}_metadata.json').read_text())
                expect(page.locator('.regime-mobile-state:visible')).to_have_count(meta['K'])
                expect(page.locator('.market-ticker')).to_have_count(2)
                expect(page.locator('[data-testid="stAlert"]:visible')).to_have_count(0)
                page.get_by_text('Filtered probability',exact=True).click();settled()
                plot=page.locator('.js-plotly-plot:visible').first
                expect(plot.locator('.modebar-btn[data-title="Zoom in"]')).to_be_visible()
                page.wait_for_function("()=>[...document.querySelectorAll('.js-plotly-plot')].find(e=>e.getClientRects().length)?._fullData?.length===2",timeout=60000)
                assert plot.evaluate('e=>e._fullData.length')==2
                check(asset,'overview_probability_overlay')
                page.get_by_text('Research evidence · tải bảng, hình và báo cáo',exact=True).click()
                with page.expect_download() as saved:
                    page.get_by_role('button',name='Tải bảng CSV',exact=True).click()
                download=saved.value
                expected=ROOT/'outputs/research_v2/deliverables/tables/T01_descriptive.csv'
                assert hashlib.sha256(Path(download.path()).read_bytes()).digest()==hashlib.sha256(expected.read_bytes()).digest()
                check(asset,'verified_csv_download')
                navigate('2.  Regime History')
                page.get_by_role('tab',name='Economic Profiles',exact=True).click()
                choose('Thống kê theo regime','Realized volatility · RV21')
                expect(page.locator('.js-plotly-plot:visible')).to_have_count(3)
                page.wait_for_function("()=>[...document.querySelectorAll('.js-plotly-plot')].find(e=>e.getClientRects().length)?._fullLayout?.xaxis?.title?.text?.includes('RV21')",timeout=60000)
                check(asset,'economic_profiles')
                page.screenshot(path=str(OUT/f'economic_{asset}_{width}.png'))
                page.get_by_role('tab',name='Transition Analysis',exact=True).click()
                page.get_by_text('NHHMM động',exact=True).click();settled()
                nn=json.loads((ROOT/f'outputs/research_v2/m3_evaluation/{asset.lower()}_metadata.json').read_text())
                heatmap=page.locator('.js-plotly-plot:visible').first
                dynamic=pd.read_csv(ROOT/f'outputs/research_v2/m3_evaluation/{asset.lower()}_dynamic_transitions.csv')
                latest=dynamic.loc[dynamic.date_utc.eq(dynamic.date_utc.max())]
                expected_matrix=latest.pivot(index='origin_state',columns='destination_state',values='conditional_probability').to_numpy().tolist()
                page.wait_for_function("expected=>{const z=[...document.querySelectorAll('.js-plotly-plot')].find(e=>e.getClientRects().length)?._fullData?.[0]?.z;return z&&z.length===expected.length&&expected.every((r,i)=>r.every((v,j)=>Math.abs(z[i][j]-v)<1e-8))}",arg=expected_matrix,timeout=60000)
                matrix=heatmap.evaluate('e=>e._fullData[0].z')
                assert len(matrix)==nn['K'] and all(abs(sum(row)-1)<1e-8 for row in matrix)
                check(asset,'dynamic_transition_K_and_probability_sums')
                page.screenshot(path=str(OUT/f'transition_{asset}_{width}.png'))
                page.get_by_role('tab',name='Market Drivers',exact=True).click()
                choose('Biến thị trường','Funding rate · tổng ngày')
                page.wait_for_function("()=>[...document.querySelectorAll('.js-plotly-plot')].find(e=>e.getClientRects().length)?._fullData?.[0]?.name?.includes('Funding')",timeout=60000)
                if 'funding_sum' not in nn['feature_names']:
                    expect(page.get_by_text('không nằm trong transition specification NHHMM đã chọn',exact=False)).to_be_visible()
                else:
                    expect(page.get_by_text('predictor trong NHHMM đã chọn',exact=False)).to_be_visible()
                expect(page.get_by_test_id('stCaptionContainer').filter(has_text='KHÔNG phải CI')).to_be_visible()
                check(asset,'drivers_roles_and_seed_range_label')
                page.screenshot(path=str(OUT/f'drivers_{asset}_{width}.png'))
                page.get_by_role('tab',name='Historical Regimes',exact=True).click()
                page.get_by_text('Smoothed · hindsight',exact=True).click();settled()
                expect(page.get_by_text('Hindsight: smoothed dùng quan sát tương lai',exact=False)).to_be_visible()
                check(asset,'hindsight_is_explicit')
                navigate('3.  Model Comparison')
                page.get_by_text('Train BIC',exact=True).click();settled()
                check(asset,'selection_metric_and_stability')
                navigate('4.  Portfolio & Risk')
                choose('Phí trên turnover','20 bps')
                expect(page.get_by_text('không áp khoảng tin cậy',exact=False)).to_be_visible()
                check(asset,'nonbaseline_fee_uncertainty_guard')
            page.close()
        browser.close()
    unchanged=all(hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest for name,digest in hashes.items())
    result={'checked_at_utc':datetime.now(timezone.utc).isoformat(),'checks':records,
            'source_sha256':hashes,'source_unchanged_during_check':unchanged,
            'status':'passed' if len(records)==32 and unchanged else 'failed'}
    (OUT/'acceptance.json').write_text(json.dumps(result,indent=2))
    if result['status']!='passed':raise SystemExit(1)


if __name__=='__main__':main()
