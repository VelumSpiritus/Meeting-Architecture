"""Remove candidate terms and let the surviving recurrence specify the jig."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json

from acoustic import AcousticParameters
from recurrence import run_recurrence


ZERO_MATRIX = ((0.0, 0.0, 0.0),) * 3


def cases():
    common = {"speaker_gain": 0.0, "load_conductance": 0.002}
    yield "candidate_passive_loaded", AcousticParameters(**common)
    yield "no_acoustic_path", AcousticParameters(**common, acoustic_coupling=(0.0, 0.0, 0.0))
    yield "no_piezo_coupling", AcousticParameters(**common, piezo_coupling=ZERO_MATRIX)
    yield "no_load", AcousticParameters(speaker_gain=0.0, load_conductance=0.0)
    yield "no_internal_electrical_loss", AcousticParameters(
        **common, electrical_conductance=0.0)
    yield "no_acoustic_loss", AcousticParameters(**common, acoustic_damping=0.0)
    yield "ideal_lossless_unloaded", AcousticParameters(
        speaker_gain=0.0, electrical_conductance=0.0,
        load_conductance=0.0, acoustic_damping=0.0)
    yield "active_return_refuter", AcousticParameters(
        speaker_gain=0.2, load_conductance=0.002)


def main() -> int:
    samples = 6000
    results = []
    for name, params in cases():
        for seed_name, compression, acoustic_seed in (
                ("quartz_compression", 1.0, 0.0),
                ("acoustic_displacement", 0.0, 1.0)):
            result = run_recurrence(params, samples=samples, compression=compression,
                                    acoustic_seed=acoustic_seed)
            result["case"] = name
            result["seed_case"] = seed_name
            results.append(result)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    destination = Path(__file__).resolve().parent / "runs" / f"ablation-{stamp}"
    destination.mkdir(parents=True, exist_ok=False)
    (destination / "summary.json").write_text(json.dumps(results, indent=2) + "\n",
                                                encoding="utf-8")
    print(destination)
    for row in results:
        energy = row["energy"]
        print(row["case"], row["seed_case"], "returns", row["event_count"],
              "first", row["first_return_time"],
              "load_work", f'{energy["delivered_load_work"]:.9g}',
              "source_work", f'{energy["active_source_work"]:.9g}',
              "closure", f'{energy["closure_residual"]:.3g}')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
