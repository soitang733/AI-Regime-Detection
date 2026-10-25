"""Evidence-based technical acceptance, separate from independent confirmation."""
import hashlib
import json
import warnings
import subprocess
from datetime import datetime,timezone
import xml.etree.ElementTree as ET
import joblib
import pandas as pd
from src.research_v2.handoff import load_hmm,UnstableResearchWarning
from src.research_v2.nhhmm_run import prepare,FAMILIES
from src.models.inference import infer
from src.utils.config import ROOT


def run():
    base=ROOT/'outputs/research_v2';checks={};detail={}
    original=json.loads((ROOT/'reports/m0_lock/baseline_manifest.json').read_text())
    changed=[p for p,v in original['files'].items() if not (ROOT/p).exists() or hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=v['sha256']]
    checks['baseline_data_models_and_paper_unchanged']=not any(p.startswith(('data/','outputs/models/','src/models/','src/data/','src/features/','paper/')) for p in changed)
    approved={
        'dashboard/app.py','dashboard/ui.py','README.md','tests/test_c3_dashboard.py',
        'tests/test_regime_radar.py','tests/test_blueprint_research.py','dashboard/research_views.py','tests/test_local_refresh.py',
        '.gitignore','pyproject.toml','requirements-dev.txt','.github/workflows/verify.yml'}
    cleanup_path=ROOT/'reports/v2_review/cleanup.json'
    cleanup=json.loads(cleanup_path.read_text()) if cleanup_path.exists() else {'apply':False,'archived_files':[]}
    archived_removed={r['path'] for r in cleanup['archived_files'] if not (ROOT/r['path']).exists()}
    checks['baseline_only_approved_existing_file_changes']=set(changed)<=approved|archived_removed
    detail['changed_baseline_files']=changed
    for asset in ['BTC','ETH']:
        with warnings.catch_warnings():
            warnings.simplefilter('ignore',UnstableResearchWarning)
            signals,metadata=load_hmm(asset,False,True)
        bundle=joblib.load(base/f'm2/{asset.lower()}.joblib')
        checks[f'{asset}_hmm_model_metadata_consistent']=json.dumps(bundle['metadata'],sort_keys=True,allow_nan=False)==json.dumps(metadata,sort_keys=True,allow_nan=False)
        frame=pd.read_parquet(base/f'm1/features_{asset.lower()}.parquet')
        features=metadata['features'];frame=frame.dropna(subset=features)
        x=bundle['scaler'].transform(frame[features]);alpha,_=infer(bundle['model'],x,frame)
        prefix,_=infer(bundle['model'],x[:100],frame.iloc[:100])
        columns=[f'prob_state_{i}' for i in range(metadata['K'])]
        error=float(abs(alpha-signals[columns].to_numpy()).max())
        checks[f'{asset}_hmm_reload_prefix_and_schema']=error<=1e-10 and abs(alpha[:100]-prefix).max()<=1e-10
        detail[f'{asset}_hmm_reload_max_error']=error
        nn=joblib.load(base/f'm3_evaluation/{asset.lower()}.joblib')
        full=pd.read_parquet(base/f'm1/features_{asset.lower()}.parquet')
        nmeta=nn['metadata'];f,nx,z,_=prepare(full,FAMILIES[nmeta['selected_family']])
        saved_metadata=json.loads((base/f'm3_evaluation/{asset.lower()}_metadata.json').read_text())
        checks[f'{asset}_nhhmm_model_metadata_consistent']=json.dumps(nmeta,sort_keys=True,allow_nan=False)==json.dumps(saved_metadata,sort_keys=True,allow_nan=False)
        na,_=nn['model'].infer(nx,z);prefix,_=nn['model'].infer(nx[:100],z[:100])
        exported=pd.read_csv(base/f'm3_evaluation/{asset.lower()}_filtered.csv')
        error=float(abs(na-exported[[f'prob_state_{i}' for i in range(nmeta['K'])]].to_numpy()).max())
        checks[f'{asset}_nhhmm_reload_prefix']=error<=1e-10 and abs(na[:100]-prefix).max()<=1e-10
        detail[f'{asset}_nhhmm_reload_max_error']=error
    manifests=['m1','m2','m3_simulation','m3','m3_evaluation','m5','deliverables','view_inputs']
    for stage in manifests:
        folder=base/stage;manifest=json.loads((folder/'manifest.json').read_text())
        hashes=manifest.get('files_sha256',{})
        checks[f'{stage}_hashes']=bool(hashes) and all((folder/name).exists() and hashlib.sha256((folder/name).read_bytes()).hexdigest()==digest for name,digest in hashes.items())
    checks['nhhmm_grid_990_completed']=json.loads((base/'m3/manifest.json').read_text())['completed']==990
    ui=json.loads((base/'ui/acceptance.json').read_text())
    checks['ui_single_result_48_passed']=len(ui['checks'])==48 and all(row['passed'] and row.get('semantic_match') for row in ui['checks'])
    checks['legacy_dashboard_removed']=not (ROOT/'dashboard/research_views.py').exists() and all(
        row.get('version')=='current' and row.get('legacy_selector_absent') for row in ui['checks'])
    checks['browser_verified_current_ui_source']=bool(ui.get('source_sha256')) and ui.get('source_unchanged_during_check') and all(
        hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest for name,digest in ui['source_sha256'].items())
    zoom_path=base/'ui/chart_zoom.json'
    zoom=json.loads(zoom_path.read_text()) if zoom_path.exists() else {'checks':[]}
    checks['chart_zoom_interactions']=len(zoom['checks'])==12 and all(
        all(row.get(name) for name in ['passed','zoom_in','zoom_out','wheel_zoom','reset']) for row in zoom['checks']) and (
        zoom.get('source_sha256')==hashlib.sha256((ROOT/'dashboard/v2_pages.py').read_bytes()).hexdigest())
    checks['zoom_chart_modules_match']=bool(zoom.get('chart_modules_sha256')) and all(
        hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest for name,digest in zoom.get('chart_modules_sha256',{}).items())
    detail['chart_zoom_cases']=len(zoom['checks'])
    terminal_path=ROOT/'reports/terminal_design/acceptance.json'
    terminal=json.loads(terminal_path.read_text()) if terminal_path.exists() else {'checks':[]}
    checks['terminal_research_interactions']=terminal.get('status')=='passed' and len(terminal['checks'])==32 and all(
        row['passed'] for row in terminal['checks']) and terminal.get('source_unchanged_during_check') and all(
        hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest for name,digest in terminal.get('source_sha256',{}).items())
    screenshots=[]
    for phase in ['before','after']:
        folder=ROOT/'reports/terminal_design'/phase
        path=folder/'manifest.json'
        capture=json.loads(path.read_text()) if path.exists() else {'screenshots':[]}
        screenshots.append(len(capture['screenshots'])==16 and all((folder/r['screenshot']).is_file() for r in capture['screenshots']))
        if phase=='after':
            screenshots.append(all(hashlib.sha256((ROOT/name.replace('\\','/')).read_bytes()).hexdigest()==digest
                for name,digest in capture.get('source_sha256',{}).items()))
    checks['terminal_before_after_screenshots']=all(screenshots)
    detail['terminal_interaction_cases']=len(terminal['checks'])
    detail['browser_checks']=len(ui['checks'])
    suite=ET.parse(base/'acceptance_pytest_final.xml').getroot()
    suites=list(suite.iter('testsuite'))
    tests=sum(int(s.attrib.get('tests',0)) for s in suites)
    failed=sum(int(s.attrib.get('failures',0))+int(s.attrib.get('errors',0)) for s in suites)
    skipped=sum(int(s.attrib.get('skipped',0)) for s in suites)
    checks['pytest_complete']=tests>=221 and failed==0 and skipped==0
    detail['pytest']={'tests':tests,'failures_errors':failed,'skipped':skipped}
    tablefiles=list((base/'deliverables/tables').glob('*.csv'));figurefiles=list((base/'deliverables/figures').glob('*.png'))
    checks['T01_to_T08_present']=all(any(p.name.startswith(f'T{i:02}') and p.stat().st_size>0 for p in tablefiles) for i in range(1,9))
    checks['F01_to_F06_both_assets_present']=all(any(p.name.startswith(f'F{i:02}_{asset}') and p.stat().st_size>0 for p in figurefiles) for i in range(1,7) for asset in ['BTC','ETH'])
    confirmation=json.loads((base/'confirmation_lock.json').read_text())
    checks['confirmation_lock_models_unchanged']=all(hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest for name,digest in confirmation['files_sha256'].items())
    locked_inputs=dict(json.loads((base/'m1/manifest.json').read_text())['inputs_sha256'])
    for stage in ['m2','m3','m4','m4_msgarch','m3_simulation']:
        locked_inputs.update(json.loads((base/stage/'input_lock.json').read_text())['inputs_sha256'])
    checks['locked_scientific_inputs_unchanged']=all(
        hashlib.sha256((ROOT/name.replace('\\','/')).read_bytes()).hexdigest()==digest for name,digest in locked_inputs.items())
    detail['locked_scientific_input_files']=len(locked_inputs)
    replay=json.loads((base/'reproduction/result.json').read_text())
    checks['full_pipeline_replay']=replay['status']=='passed' and len(replay['stages'])==13 and all(
        r['exit_code']==0 for r in replay['stages']) and replay['original_artifacts_unchanged'] and all(
        r['passed'] for r in replay['csv_comparisons'])
    review=base/'review';review_manifest=json.loads((review/'manifest.json').read_text())
    checks['review_hashes']=all(hashlib.sha256((review/name).read_bytes()).hexdigest()==digest
        for name,digest in review_manifest['files_sha256'].items())
    source_hashes=review_manifest.get('source_sha256',{})
    checks['review_source_matches']=bool(source_hashes) and all(
        hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest for name,digest in source_hashes.items())
    before=json.loads((review/'input_snapshot.json').read_text())['inputs_sha256']
    scientific_changes=[name for name,digest in before.items() if not (ROOT/name).exists() or
        hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=digest]
    checks['pre_review_scientific_artifacts_unchanged']=not scientific_changes
    detail['pre_review_artifacts']={'checked':len(before),'changed':scientific_changes}
    rolling=json.loads((review/'rolling_benchmarks/manifest.json').read_text())
    checks['rolling_development_benchmarks_complete']=rolling['completed']==rolling['planned']==120 and not rolling['test_used'] and not rolling['champion_changed']
    checks['rolling_benchmark_hashes']=all(hashlib.sha256((review/'rolling_benchmarks'/name).read_bytes()).hexdigest()==digest
        for name,digest in rolling['files_sha256'].items())
    numerics=pd.read_csv(review/'T05_selected_numerics.csv')
    checks['review_nhhmm_numerics']=bool((numerics.probability_error<=1e-8).all() and
        (numerics.reload_max_error<=1e-10).all() and (numerics.prefix_max_error<=1e-10).all() and
        (numerics.forecast_reload_max_error<=1e-10).all() and
        numerics.converged.all() and numerics.last_optimizer_success.all() and (numerics.objective_max_increase<=1e-7).all())
    exported_performance=pd.read_csv(base/'m5/performance.csv')
    baseline_performance=exported_performance.loc[exported_performance.scenario.eq('baseline_close_to_close')&exported_performance.fee_rate.eq(.001)]
    intervals=pd.read_csv(review/'T06_absolute_uncertainty.csv')
    matched=intervals.loc[intervals.block_days.eq(21)&intervals.metric.isin(['Sharpe','max_drawdown'])].merge(
        baseline_performance,on=['asset','strategy'],validate='many_to_one')
    checks['review_backtest_points_match_frozen_results']=len(matched)==16 and all(
        abs(row.point-getattr(row,row.metric))<=1e-10 for row in matched.itertuples())
    command=['git','-c',f'safe.directory={ROOT.as_posix()}','-C',str(ROOT)]
    fsck=subprocess.run(command+['fsck','--full','--no-reflogs'],capture_output=True)
    (ROOT/'reports/v2_review/git_fsck.log').write_bytes(fsck.stdout+fsck.stderr)
    checks['git_history_integrity']=fsck.returncode==0
    m0=json.loads((ROOT/'reports/m0_lock/lock_manifest.json').read_text())
    baseline=subprocess.run(command+['show','refs/archive/v2-before-cleanup:reports/m0_lock/baseline.zip'],capture_output=True)
    checks['M0_snapshot_recoverable_from_git']=baseline.returncode==0 and hashlib.sha256(baseline.stdout).hexdigest()==m0['files_sha256']['baseline.zip']
    history=json.loads((ROOT/'reports/v2_review/repository_history.json').read_text())
    snapshot=next(h for h in history['history'] if h['ref']=='refs/archive/v2-before-cleanup')
    checks['cleanup_files_archived']=all(snapshot['verified_sha256'].get(row['path'])==row['sha256'] for row in cleanup['archived_files'])
    retained=cleanup.get('user_decision')=='retain_listed_files'
    checks['repository_single_V2_worktree']=not any(
        (ROOT/name).exists() for name in ['AI-Regime-Detection-commit','AI-Regime-Detection-main','local-demo-20261024'])
    checks['legacy_files_match_user_decision']=(cleanup['apply'] and not any(ROOT.rglob('*.zip'))) or (
        retained and all((ROOT/row['path']).exists() and hashlib.sha256((ROOT/row['path']).read_bytes()).hexdigest()==row['sha256']
            for row in cleanup['archived_files']))
    detail['retained_legacy_files']=len(cleanup['archived_files']) if retained else 0
    detail['pipeline_replay']={'stages':len(replay['stages']),'csv_comparisons':len(replay['csv_comparisons']),
        'fresh_fits':replay['fresh_model_fits'],'mode':replay['mode']}
    detail['additional_rolling_fits']=rolling['completed']
    checks={name:bool(value) for name,value in checks.items()}
    result={'checked_at_utc':datetime.now(timezone.utc).isoformat(),'technical_status':'passed' if all(checks.values()) else 'failed',
        'independent_research_confirmation':'pending','checks':checks,'details':detail,
        'limitations':['Historical test reused: exploratory.', 'Macro release vintages not verified.',
                      'Legacy documents/ZIPs/caches retained at explicit user request; not active V2 results.',
                      'Zoom125% was emulated by viewport/device scale, not browser toolbar.',
                      'No independent clean-room replication or prospective performance confirmation.']}
    (base/'technical_acceptance.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))
    if not all(checks.values()):raise SystemExit(1)


if __name__=='__main__':run()
