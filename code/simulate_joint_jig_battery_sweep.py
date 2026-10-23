from datetime import datetime, timezone
from pathlib import Path
import json
from joint_jig_battery_sweep import sweep

r=sweep()
stamp=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
out=Path("runs")/("joint-jig-battery-"+stamp); out.mkdir(parents=True)
(out/"summary.json").write_text(json.dumps(r,indent=2),encoding="utf-8")
print("scenarios",len(r["rows"]))
for row in r["rows"]:
    p=row["parameters"]
    if p["contact_efficiency"]==.1 and p["piezo_efficiency"]==.01:
        print(f"sound={p['acoustic_power_w']:g} W -> rectified={row['power']['rectified_electrical_w']:.6g} W, "
              f"battery={row['power']['battery_average_w']:.6g} W, "
              f"added={row['battery']['mah_added']:.6g} mAh, cold={row['cold_start_s']}")
print("best",max(r["rows"],key=lambda x:x["battery"]["accepted_j"])["battery"])
print("max_closure",max(abs(x["closure_residual_j"]) for x in r["rows"]))
print("WROTE",out/"summary.json")
