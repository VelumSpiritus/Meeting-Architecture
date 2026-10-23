from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json

from dual_storage_jig import run_battery_branch, run_measure_branch


def main():
    energies = (1e-10, 1e-9, 1e-8, 1e-7, 1e-6)
    result = {}
    for value in energies:
        key = f"{value:.0e}_joule_per_event"
        result[key] = {"measure": run_measure_branch(value),
                       "battery": run_battery_branch(value)}
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    destination = Path(__file__).resolve().parent / "runs" / f"dual-storage-{stamp}"
    destination.mkdir(parents=True, exist_ok=False)
    (destination / "summary.json").write_text(json.dumps(result, indent=2) + "\n",
                                                encoding="utf-8")
    print(destination)
    print("event_J    measure_V  cold_start_s  battery_J    SOC_gain       operating_J")
    for key, case in result.items():
        battery = case["battery"]
        cold = battery["cold_start_time"]
        print(f'{case["measure"]["event_energy"]:.0e}  '
              f'{case["measure"]["buffer_voltage"]:>11.6f}  '
              f'{str(None if cold is None else round(cold, 3)):>12}  '
              f'{battery["battery"]["accepted_energy"]:>10.6g}  '
              f'{battery["battery"]["soc_gain"]:>12.6g}  '
              f'{battery["energy"]["harvester_operating_loss"]:>11.6g}')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
