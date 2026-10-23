from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json

from acoustic import AcousticParameters
from carry import CarryParameters, run_carry


def main() -> int:
    body = AcousticParameters(speaker_gain=0.0, load_conductance=0.0,
                              electrical_conductance=0.0, acoustic_damping=0.0)
    results = [run_carry(body, CarryParameters(face_cut=cut,
                                               storage_capacitance=capacitance,
                                               carry_inductance=inductance,
                                               carry_resistance=0.0))
               for cut in range(3)
               for capacitance in (1.0, 4.0)
               for inductance in (0.25, 1.0, 4.0)]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    destination = Path(__file__).resolve().parent / "runs" / f"carry-{stamp}"
    destination.mkdir(parents=True, exist_ok=False)
    (destination / "summary.json").write_text(json.dumps({
        "epistemic_status": ("normalized continuous carry topology; face axis and dimensional "
                             "circuit parameters remain measurement residuals"),
        "results": results}, indent=2) + "\n", encoding="utf-8")
    print(destination)
    for result in results:
        c, s = result["carry_parameters"], result["storage"]
        print("cut", c["face_cut"], "Cs", c["storage_capacitance"],
              "L", c["carry_inductance"], "peak", f'{s["peak_energy"]:.9g}',
              "final", f'{s["final_energy"]:.9g}', "monotonic", s["monotonic"],
              "closure", f'{result["energy"]["closure_residual"]:.3g}')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
