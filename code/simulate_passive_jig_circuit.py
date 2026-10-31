from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json

from passive_jig_circuit import JigCircuitParameters, run_jig_circuit


def main():
    cases = {
        "ideal_bridge": run_jig_circuit(
            parameters=JigCircuitParameters(diode_drop=0.0, leakage_conductance=0.0)),
        "low_drop_bridge": run_jig_circuit(
            parameters=JigCircuitParameters(diode_drop=0.02, leakage_conductance=1e-5)),
        "schottky_like_drop": run_jig_circuit(
            parameters=JigCircuitParameters(diode_drop=0.2, leakage_conductance=1e-5)),
    }
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    destination = Path(__file__).resolve().parent / "runs" / f"passive-jig-{stamp}"
    destination.mkdir(parents=True, exist_ok=False)
    (destination / "summary.json").write_text(json.dumps(cases, indent=2) + "\n",
                                                encoding="utf-8")
    print(destination)
    print("case                 voltage    held/input  conducts  closure")
    for name, result in cases.items():
        e = result["energy"]
        ratio = e["held"] / e["mechanical_input"] if e["mechanical_input"] else 0.0
        print(f'{name:20} {result["reservoir"]["voltage"]:>9.6f}  {ratio:>10.6f}  '
              f'{result["conduction_events"]:>8}  {e["closure_residual"]:.3g}')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
