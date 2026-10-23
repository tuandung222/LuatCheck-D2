from pathlib import Path
import concurrent.futures,json,sqlite3,uuid,requests
ROOT=Path(__file__).resolve().parent
BASE='http://127.0.0.1:8011'
c=sqlite3.connect(ROOT/'web.sqlite3'); c.row_factory=sqlite3.Row
r=dict(c.execute("select * from runs where terminal_status='answered' order by created_at limit 1").fetchone())
b=dict(c.execute('select * from browser_sessions where session_id=?',(r['session_id'],)).fetchone())
a=requests.Session();a.cookies.set('luatcheck_session',b['session_id'])
headers={'Origin':BASE,'X-CSRF-Token':b['csrf_token']}
other=requests.Session();other_csrf=other.get(BASE+'/api/v1/session').json()['csrf_token']
checks=[]
def record(name,ok,observed):
 checks.append({'check':name,'pass':bool(ok),'observed':observed})
def post(path,body,extra=None):return a.post(BASE+'/api/v1'+path,json=body,headers={**headers,**(extra or {})},timeout=15)
def save(name,value):(ROOT/name).write_text(json.dumps(value,ensure_ascii=False,indent=2))
row=a.get(BASE+'/api/v1/runs/'+r['run_id']).json(); save('native-answer.json',row)
record('native_answer',row['terminal_status']=='answered' and not row['snapshot']['final_output']['from_cache'],row['snapshot']['usage'])
for suffix in ['', '/events', '/articles/Dieu_26']:
 resp=other.get(BASE+'/api/v1/runs/'+r['run_id']+suffix,timeout=10)
 record('foreign_session'+suffix,resp.status_code==404,resp.status_code)
payload={'query':r['query_text'],'pasted_document':r['pasted_document'],'verification_mode':r['verification_mode']}
resp=post('/runs',payload,{'Idempotency-Key':r['request_key']})
record('same_request_key_replay',resp.status_code==202 and resp.json().get('run_id')==r['run_id'],resp.json())
resp=post('/runs',{**payload,'query':payload['query']+' ' +str(uuid.uuid4())},{'Idempotency-Key':r['request_key']})
record('changed_request_key_conflict',resp.status_code==409,resp.status_code)
resp=a.post(BASE+'/api/v1/runs',json=payload,headers={'Origin':BASE,'Idempotency-Key':str(uuid.uuid4())})
record('missing_csrf',resp.status_code==403,resp.status_code)
resp=post('/runs',payload,{'Origin':'https://example.invalid','Idempotency-Key':str(uuid.uuid4())})
record('foreign_origin',resp.status_code==403,resp.status_code)
resp=post('/runs',{**payload,'verification_mode':'semantic_entailment'},{'Idempotency-Key':str(uuid.uuid4())})
record('disabled_semantic',resp.status_code==422,resp.status_code)
article=a.get(BASE+f"/api/v1/runs/{r['run_id']}/articles/Dieu_26").json(); save('article.json',article)
quote=row['snapshot']['final_output']['citations'][0]['exact_quote']
record('citation_exact_match',' '.join(quote.split()) in ' '.join(article['content'].split()),{'article_id':article['article_id'],'pages':article['source_pages'],'source_sha256':article['source_sha256']})
text=a.get(BASE+f"/api/v1/runs/{r['run_id']}/events",timeout=10).text
(ROOT/'events.sse').write_text(text)
ids=[int(line[4:]) for line in text.splitlines() if line.startswith('id: ')]
resume=a.get(BASE+f"/api/v1/runs/{r['run_id']}/events",headers={'Last-Event-ID':str(ids[-1])},timeout=10).text
record('sse_resume_after_last_event','id:' not in resume,{'event_count':len(ids),'resume':resume})
p=post(f"/runs/{r['run_id']}/summary-proposals",{'recipient':'payload-review@example.invalid','content':row['snapshot']['final_output']['content']}).json()
resp=post(f"/summary-proposals/{p['proposal_id']}/confirm",{'payload_hash':'0'*64})
record('tampered_approval_hash',resp.status_code==409,resp.status_code)
resp=other.post(BASE+f"/api/v1/summary-proposals/{p['proposal_id']}/confirm",json={'payload_hash':p['payload_hash']},headers={'Origin':BASE,'X-CSRF-Token':other_csrf})
record('foreign_proposal',resp.status_code==404,resp.status_code)
outbox=ROOT/'outbox.jsonl'
count=lambda:len(outbox.read_text().splitlines()) if outbox.exists() else 0
before=count()
resp=post(f"/summary-proposals/{p['proposal_id']}/confirm",{'payload_hash':p['payload_hash']})
record('local_outbox_receipt',resp.status_code==200 and count()==before+1,resp.json())
resp=post(f"/summary-proposals/{p['proposal_id']}/confirm",{'payload_hash':p['payload_hash']})
record('outbox_confirm_retry',resp.status_code==200 and count()==before+1 and resp.json().get('replayed'),{'status':resp.status_code,'rows':count()})
# Real simultaneous HTTP requests, no replaced components.
def same_proposal(_):
 res=requests.post(BASE+f"/api/v1/runs/{r['run_id']}/summary-proposals",json={'recipient':'concurrent-review@example.invalid','content':row['snapshot']['final_output']['content']},headers=headers,cookies={'luatcheck_session':b['session_id']},timeout=20)
 return {'status':res.status_code,'body':res.text[:200]}
with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
 concurrent=list(pool.map(same_proposal,range(12)))
record('concurrent_identical_proposal',all(x['status']==200 for x in concurrent),concurrent)
save('api-checks.json',checks)
print(json.dumps(checks,ensure_ascii=False,indent=2))
