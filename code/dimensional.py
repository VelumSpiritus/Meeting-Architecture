"""Dimensional readings derived from measured crystal geometry.

This is deliberately separate from the normalized modal body.  It converts
physical evidence into bounded quantities without assigning an unknown crystal
axis or distributing total mass among modes.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
import json
from pathlib import Path


@dataclass(frozen=True)
class SlabEvidence:
    length_m: float = 0.0381
    width_m: float = 0.03175
    thickness_m: float = 0.0127
    mass_kg: float = 0.028
    quartz_density_kg_m3: float = 2649.0
    meter_resistance_ohm: float = 1_000_000.0
    # Alpha-quartz permittivity at constant strain, two principal values.
    permittivity_low_f_m: float = 39.21e-12
    permittivity_high_f_m: float = 41.03e-12
    # Magnitude band from alpha-quartz strain-charge constants. Orientation
    # determines which projection, sign, or zero applies at Face A <-> Face B.
    piezo_d_low_c_n: float = 0.67e-12
    piezo_d_high_c_n: float = 4.6e-12


def parallel_plate_capacitance(permittivity_f_m, area_m2, separation_m):
    if area_m2 <= 0.0 or separation_m <= 0.0 or permittivity_f_m <= 0.0:
        raise ValueError("permittivity, area and separation must be positive")
    return permittivity_f_m * area_m2 / separation_m


def derive(evidence=SlabEvidence(), minimum_area_fraction=0.25):
    if not 0.0 < minimum_area_fraction <= 1.0:
        raise ValueError("minimum_area_fraction must lie in (0, 1]")
    maximum_area = evidence.length_m * evidence.width_m
    minimum_area = minimum_area_fraction * maximum_area
    capacitance_low = parallel_plate_capacitance(
        evidence.permittivity_low_f_m, minimum_area, evidence.thickness_m
    )
    capacitance_high = parallel_plate_capacitance(
        evidence.permittivity_high_f_m, maximum_area, evidence.thickness_m
    )
    tau_low = evidence.meter_resistance_ohm * capacitance_low
    tau_high = evidence.meter_resistance_ohm * capacitance_high
    box_volume = evidence.length_m * evidence.width_m * evidence.thickness_m
    material_volume = evidence.mass_kg / evidence.quartz_density_kg_m3
    return {
        "evidence": asdict(evidence),
        "area": {
            "maximum_broad_face_m2": maximum_area,
            "modeled_effective_fraction_range": [minimum_area_fraction, 1.0],
            "status": "range assumption only; electrode overlap is not measured",
        },
        "capacitance_f": {"low": capacitance_low, "high": capacitance_high},
        "capacitance_pf": {"low": capacitance_low * 1e12, "high": capacitance_high * 1e12},
        "meter_rc_seconds": {"low": tau_low, "high": tau_high},
        "meter_rc_microseconds": {"low": tau_low * 1e6, "high": tau_high * 1e6},
        "mass_geometry": {
            "bounding_box_volume_cm3": box_volume * 1e6,
            "box_averaged_mass_density_g_cm3": evidence.mass_kg / box_volume / 1000.0,
            "inferred_quartz_material_volume_cm3": material_volume * 1e6,
            "inferred_box_occupancy_fraction": material_volume / box_volume,
            "status": "volume and occupancy inferred from exact mass plus reference alpha-quartz density; not a direct displacement reading",
        },
        "measurement_projection": (
            "DT-103 is a load, not an open-circuit witness; a static piezo charge "
            "decays on the derived RC scale before an ordinary display can be relied upon"
        ),
        "residual": [
            "crystallographic axis through Face A and Face B",
            "actual electrode overlap area",
            "meter input capacitance and update aperture",
            "contact leakage and surface moisture",
            "applied force profile",
        ],
    }


def force_sweep(evidence=SlabEvidence(), area_fractions=(0.25, 0.5, 1.0),
                forces_n=(0.1, 1.0, 5.0), hold_targets_s=(0.1, 1.0)):
    """Bound Q=dF and V=Q/C without assigning the unknown crystal axis."""
    maximum_area = evidence.length_m * evidence.width_m
    rows = []
    for area_fraction in area_fractions:
        if not 0.0 < area_fraction <= 1.0:
            raise ValueError("area fractions must lie in (0, 1]")
        area = maximum_area * area_fraction
        capacitance_low = parallel_plate_capacitance(
            evidence.permittivity_low_f_m, area, evidence.thickness_m
        )
        capacitance_high = parallel_plate_capacitance(
            evidence.permittivity_high_f_m, area, evidence.thickness_m
        )
        for force in forces_n:
            if force < 0.0:
                raise ValueError("force magnitude must be non-negative")
            charge_low = evidence.piezo_d_low_c_n * force
            charge_high = evidence.piezo_d_high_c_n * force
            rows.append({
                "area_fraction": area_fraction,
                "area_mm2": area * 1e6,
                "force_n": force,
                "charge_pc": {"low": charge_low * 1e12, "high": charge_high * 1e12},
                # Conservative crossing: smallest Q / largest C, largest Q / smallest C.
                "open_circuit_voltage_v": {
                    "low": charge_low / capacitance_high,
                    "high": charge_high / capacitance_low,
                },
                "dt103_tau_microseconds": {
                    "low": evidence.meter_resistance_ohm * capacitance_low * 1e6,
                    "high": evidence.meter_resistance_ohm * capacitance_high * 1e6,
                },
                "resistance_for_hold_ohm": {
                    str(target): {
                        "low": target / capacitance_high,
                        "high": target / capacitance_low,
                    } for target in hold_targets_s
                },
            })
    return {
        "model": "Q=dF; C=epsilon*A/t; V=Q/C; tau=R*C",
        "status": "orientation envelope, not a prediction for Face A <-> Face B",
        "rows": rows,
        "rho3": {
            "claim_refuted": "DT-103 display can be treated as the open-circuit peak",
            "witness": "derived RC is microseconds while a handheld display is not a microsecond peak instrument",
        },
        "residual": [
            "Face A <-> Face B crystallographic projection and sign",
            "actual force transmitted through the compliant contact",
            "actual electrode area",
            "strain distribution around internal fractures",
        ],
    }


def write_report(path=None):
    destination = path or Path(__file__).resolve().parent / "crystal" / "dimensional.json"
    report = derive()
    destination.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return destination, report


def write_sweep(path=None):
    destination = path or Path(__file__).resolve().parent / "crystal" / "force_sweep.json"
    report = force_sweep()
    destination.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return destination, report


if __name__ == "__main__":
    destination, report = write_report()
    sweep_destination, sweep = write_sweep()
    print(destination)
    print("capacitance_pf", report["capacitance_pf"])
    print("meter_rc_microseconds", report["meter_rc_microseconds"])
    print(sweep_destination)
    print("sweep rows", len(sweep["rows"]))
