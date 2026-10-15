"""Validate the sanitized text sample; does not rerun FreeCAD."""
from pathlib import Path
import collections,hashlib,json,re
root=Path(__file__).resolve().parent
manifest=json.loads((root/'manifest.json').read_text())
for f in manifest['files']:
 p=root/f['path'];assert p.stat().st_size==f['bytes'],p.name
 assert hashlib.sha256(p.read_bytes()).hexdigest()==f['sha256'],p.name
trajectory=json.loads((root/'build-trajectory.json').read_text())
training=json.loads((root/'training.jsonl').read_text())
assert training['messages']==[{k:v for k,v in m.items() if k!='source_sequence'} for m in trajectory['messages']]
pending=set();calls=collections.Counter();results=collections.Counter()
for m in training['messages']:
 assert m['role'] in ('user','assistant','tool')
 for c in m.get('tool_calls',[]):
  assert c['id'] not in pending
  pending.add(c['id']);calls[c['id']]+=1
  json.loads(c['function']['arguments'])
 if m['role']=='tool':
  assert m['tool_call_id'] in pending
  pending.remove(m['tool_call_id']);results[m['tool_call_id']]+=1
assert not pending and calls==results and len(calls)==63
records=[json.loads(l) for l in (root/'sanitized-records.jsonl').read_text().splitlines()]
assert len(records)==229
assert sum(r['kind']=='execution_detail' for r in records)==89
v=json.loads((root/'validation.json').read_text())
assert v['objects']==677 and v['solid_count']==339
assert not any(v[k] for k in ('invalid_shapes','solver_errors','unconstrained_sketches','column_footprint_errors'))
assert len(v['opening_checks'])==24 and all(o['through_at_center'] for o in v['opening_checks'])
assert v['parameter_edit_verified'] and v['step_roundtrip']['valid']
assert len(v['elevation_checks'])==9 and len(v['stair_level_checks'])==8
for f in manifest['files']:
 if f['path']=='validate_sample.py':continue # Scanner rules themselves contain generic sentinels.
 s=(root/f['path']).read_text()
 assert not re.search(r'/Users/|data:image/[^;]+;base64,',s)
 assert not re.search(r'\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b',s,re.I)
print('PASS: file hashes, training formats, 63 paired calls, 229 records, historical acceptance evidence, privacy sentinels.')
