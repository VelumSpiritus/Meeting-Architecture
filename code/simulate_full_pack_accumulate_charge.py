from datetime import datetime,timezone
from pathlib import Path
import json
from full_pack_accumulate_charge import sweep_full_pack
r=sweep_full_pack(); stamp=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
out=Path('runs')/('full-pack-'+stamp); out.mkdir(parents=True)
(out/'summary.json').write_text(json.dumps(r,indent=2),encoding='utf-8')
print('scenarios',r['scenarios'],'completed',r['completed'])
for x in r['fastest']:
 p=x['parameters']; print('days',round(x['elapsed_days'],4),'crystals',p['crystals'],
 'contact',p['contact_fraction'],'piezo',p['piezo_fraction'],'resonance',p['resonance_capture_gain'],
 'harvest_W',round(x['power']['harvested_w'],6),'minutes',x['steps_executed'],
 'closure_J',x['energy']['closure_j'])
print('WROTE',out/'summary.json')
