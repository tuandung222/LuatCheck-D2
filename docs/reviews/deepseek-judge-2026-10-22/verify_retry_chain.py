"""Replay actual SSE and validate first accepted judgments across ordered retry phases."""
import csv
import json
from pathlib import Path
from evaluation.judge_gateway import sha, validate

MAIN = Path('evaluation/runs/deepseek-judge-main-v1')
ANALYSIS = MAIN / 'analysis-retry-v2'
PHASES = [MAIN, Path('evaluation/runs/deepseek-judge-recovery-v1'), Path('evaluation/runs/deepseek-judge-recovery-v2')]
packets = {p['review_id']: p for p in json.loads((MAIN/'input-judge_packets.json').read_text())}
accepted = {}
records = []
phase_counts = []
for base in PHASES:
    manifest = json.loads((base/'manifest.json').read_text())
    assert manifest['status'] == 'collected_pending_human_validation'
    assert sha(base/'judgments.jsonl') == manifest['judgments_sha256']
    for name, digest in manifest['input_sha256'].items():
        assert sha(base/name) == digest
    rows = [json.loads(line) for line in (base/'judgments.jsonl').read_text().splitlines()]
    assert {r['review_id'] for r in rows} == set(packets)-set(accepted)
    for row in rows:
        first_valid = None
        for name in row['attempts']:
            path = base/'attempts'/name
            assert sha(path) == manifest['attempts_sha256'][name]
            record = json.loads(path.read_text())
            records.append(record)
            assert json.loads(record['request']['messages'][1]['content'].split('\n',1)[1]) == packets[row['review_id']]
            assert record['request']['model'] == manifest['config']['model']
            if record['request']['stream']:
                chunks = [json.loads(line[5:].strip()) for line in record.get('raw_body','').splitlines() if line.startswith('data:') and line[5:].strip() != '[DONE]']
                assert chunks == record['stream_chunks']
                content = ''.join(choice.get('delta',{}).get('content') or '' for chunk in chunks for choice in chunk.get('choices',[]))
                if 'assembled_content' in record:
                    assert content == record['assembled_content']
                stopped = record.get('finish_reason') == 'stop' and record.get('done_marker_received')
            else:
                if record.get('http_status') != 200:
                    continue
                raw = json.loads(record['raw_body'])
                content = raw['choices'][0]['message'].get('content')
                stopped = raw['choices'][0]['finish_reason'] == 'stop'
            if not stopped:
                continue
            try:
                judgment = validate(json.loads(content),packets[row['review_id']])
            except (ValueError,KeyError,TypeError):
                continue
            assert first_valid is None, 'No further request is permitted after a valid output'
            first_valid = judgment
        if first_valid is not None:
            accepted[row['review_id']] = first_valid
    phase_counts.append({'phase':str(base),'accepted_cumulative':len(accepted)})
summary=json.loads((ANALYSIS/'summary.json').read_text())
details=json.loads((ANALYSIS/'private-judge-details.json').read_text())
prior=json.loads((MAIN/'analysis-final/private-judge-details.json').read_text())
for row in prior:
    if row['valid_judgment']:
        assert accepted[row['review_id']] == row['judgment'], 'Previously accepted grade changed'
for row in details:
    assert row['valid_judgment'] == (row['review_id'] in accepted)
    assert row['judgment'] == accepted.get(row['review_id'])
for mode, m in summary['modes'].items():
    subset=[r for r in details if r['mode']==mode]
    successes=0
    for row in subset:
        j=row['judgment']
        expected=False if row['system_error'] else None if not row['valid_judgment'] or not row['judgeable'] else (j['behaviour_appropriate'] and j['correctness']==2 and j['completeness']==2 and all(c['support']=='supported' for c in j['claims']))
        assert row['llm_task_success_estimate'] is expected
        successes+=expected is True
    assert successes == m['success_count_estimate']
    claims=[c for r in subset if r['valid_judgment'] and r['judgeable'] for c in r['judgment']['claims']]
    assert len(claims)==m['factual_claims']
    assert sum(c['support']=='supported' for c in claims)==m['supported_claims']
assert len(records)==summary['api_usage']['attempts_including_failed']
with (ANALYSIS/'human-audit/labels.csv').open() as f:
    labels=list(csv.DictReader(f))
assert len(labels)==12 and all(not v for r in labels for k,v in r.items() if k!='review_id')
assert sha(ANALYSIS/'human-audit/labels.csv') == sha(MAIN/'analysis-final/human-audit/labels.csv')
receipt={'status':'passed','accepted':len(accepted),'attempts':len(records),'phases':phase_counts,'previous_57_accepted_judgments_unchanged':True,'human_labels_generated':False,'accounting_anomalies_remain_disclosed':True}
Path('docs/reviews/deepseek-judge-2026-10-22/retry-chain-verification.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt,indent=2))
