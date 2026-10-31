import json
from datetime import datetime, timezone
from pathlib import Path

from battery_form import BatteryFormParameters, occam_ablation


def main():
    result = occam_ablation(BatteryFormParameters())
    run_id = "battery-form-"+datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    folder = Path(__file__).resolve().parent/"runs"/run_id
    folder.mkdir(parents=True)
    path = folder/"summary.json"
    path.write_text(json.dumps(result, indent=2, sort_keys=True)+"\n", encoding="utf-8")
    full = result["rows"]["full"]
    print(json.dumps({
        "status": full["status"],
        "per_application": full["per_application"],
        "formation": full["formation"],
        "indispensable_functions": result["indispensable_functions"],
        "minimum_external_jig_organs_if_pack_protection_is_verified":
            result["minimum_external_jig_organs_if_pack_protection_is_verified"],
        "wrote": str(path),
    }, indent=2))


if __name__ == "__main__":
    main()
