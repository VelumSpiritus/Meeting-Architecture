from __future__ import annotations

import json
from datetime import datetime, timezone
from math import acos, pi
from pathlib import Path

from measured_crystal_surrogate import (PE_EMIS_FREE, RUS_CLAMPED,
                                        SurrogateRun, measured_event,
                                        recur_measured_orientation)
from quartz_tensor_orientation import rotation_z_y_z


def orientations(step=15):
    polar_count = 180 // step
    for a in range(0, 360, step):
        for bi in range(polar_count):
            beta = acos(-1+2*(bi+.5)/polar_count)
            for g in range(0, 360, step):
                yield [a, beta*180/pi, g], rotation_z_y_z(a*pi/180, beta,
                                                          g*pi/180)


def main():
    root = Path(__file__).parent
    out = root / "runs" / ("measured-surrogate-" + datetime.now(
        timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ"))
    out.mkdir(parents=True)
    run = SurrogateRun()
    report = {"source_specimen": {
        "dimensions_mm": [15.06, 30.10, 20.03], "mass_g": 24.03,
        "measured_modes_khz": [50, 310], "temperature_c": 25,
        "source": "Xie, Bai & Li, arXiv:2212.00284"},
        "owner_surrogate": {"dimensions_mm": [38.1, 31.75, 12.7],
                            "mass_g": 28.0}, "materials": {}}
    for material in (PE_EMIS_FREE, RUS_CLAMPED):
        samples = []
        for angles, rotation in orientations():
            event = measured_event(run.force, rotation, material, run)
            samples.append((event["coupling_fraction"], angles, rotation, event))
        samples.sort(key=lambda item: item[0])
        picks = {name: samples[round(q*(len(samples)-1))]
                 for name, q in (("p05", .05), ("median", .5),
                                 ("p95", .95), ("maximum", 1.0))}
        cases = {}
        for name, (_, angles, rotation, event) in picks.items():
            result = recur_measured_orientation(rotation, material, run)
            cases[name] = {"euler_degrees": angles, "first_event": event,
                           "recurrence": result}
        report["materials"][material.name] = {
            "orientation_count": len(samples), "cases": cases}
    (out / "summary.json").write_text(json.dumps(report, indent=2))
    print(out)
    print("material                cut      coupling   first_Vmax  initial_uJ held_uJ")
    for material, data in report["materials"].items():
        for cut, case in data["cases"].items():
            event = case["first_event"]
            rec = case["recurrence"]
            vmax = max(abs(v) for v in event["face_voltage_volt"])
            print(f"{material:23} {cut:8} {event['coupling_fraction']:9.6f} "
                  f"{vmax:11.5f} {rec['initial_mechanical_joule']*1e6:10.6f} "
                  f"{rec['energy']['held_joule']*1e6:8.6f}")


if __name__ == "__main__":
    main()
