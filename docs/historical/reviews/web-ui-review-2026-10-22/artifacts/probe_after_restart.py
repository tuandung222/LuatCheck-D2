from pathlib import Path
import json,requests,sqlite3
p=Path(__file__).resolve().parent;c=sqlite3.connect(p/'web.sqlite3');c.row_factory=sqlite3.Row
r=dict(c.execute("select * from runs where terminal_status='answered' limit 1").fetchone());b=dict(c.execute('select * from browser_sessions where session_id=?',(r['session_id'],)).fetchone())
s=requests.Session();s.cookies.set('luatcheck_session',b['session_id']);base='http://127.0.0.1:8011';headers={'Origin':base,'X-CSRF-Token':b['csrf_token']}
rows=s.get(base+'/api/v1/runs').json()
(p/'runs-after-restart.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2))
prop=dict(c.execute("select * from summary_proposals where recipient='restart-review@example.invalid'").fetchone())
resp=s.post(base+f"/api/v1/runs/{r['run_id']}/summary-proposals",json={'recipient':prop['recipient'],'content':prop['content']},headers=headers)
checks={'restarted_run_snapshot_keys':[{'run_id':x['run_id'],'terminal_status':x['terminal_status'],'snapshot_keys':list((x['snapshot'] or {}).keys())} for x in rows['items']],'renew_expired_proposal':{'http_status':resp.status_code,'old_id':prop['proposal_id'],'result':resp.json()},'outbox_rows':len((p/'outbox.jsonl').read_text().splitlines())}
(p/'restart-checks.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2));print(json.dumps(checks,ensure_ascii=False,indent=2))
# Isolated configured native client aimed at an actually closed port, no replacement server.
import yaml
cfg=yaml.safe_load((p/'review-config.yaml').read_text());cfg['model']['endpoint']='http://127.0.0.1:9'
(p/'unavailable-config.yaml').write_text(yaml.safe_dump(cfg,allow_unicode=True,sort_keys=False))
