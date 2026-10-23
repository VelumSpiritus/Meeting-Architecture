"""Dimension-free tournament for passive quartz carry topologies.

This compares spatial observability and recurrence, not component performance.
Every topology receives the same normalized field seeds and the same conversion
efficiency.  A cut bank is evaluated as the subspace its ports can observe;
state-derived h-prime is evaluated as a fresh cut on the returned residual.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import sqrt


TOLERANCE = 1e-12


def dot(left, right):
    return sum(a * b for a, b in zip(left, right))


def scale(amount, vector):
    return [amount * value for value in vector]


def subtract(left, right):
    return [a - b for a, b in zip(left, right)]


def unit(vector):
    magnitude = sqrt(dot(vector, vector))
    return scale(1.0 / magnitude, vector) if magnitude > TOLERANCE else None


def energy(vector):
    return 0.5 * dot(vector, vector)


def orthogonal_basis(cuts):
    """Return the independent observable directions without double counting."""
    basis = []
    for candidate in cuts:
        residual = list(candidate)
        for direction in basis:
            residual = subtract(residual, scale(dot(direction, residual), direction))
        direction = unit(residual)
        if direction is not None:
            basis.append(direction)
    return basis


@dataclass(frozen=True)
class Topology:
    key: str
    label: str
    cuts: tuple[tuple[float, float, float], ...]
    recurrence: str = "fixed_bank"
    ports: int = 1
    reactive_elements: int = 0
    switches: int = 0
    conditional: str | None = None


DIAGONAL = (1 / sqrt(3),) * 3
MODES = ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))
ROTATED_MODES = (
    DIAGONAL,
    (1 / sqrt(2), -1 / sqrt(2), 0.0),
    (1 / sqrt(6), 1 / sqrt(6), -2 / sqrt(6)),
)
SEGMENTS = tuple(
    tuple(sign / sqrt(3) for sign in signs)
    for signs in ((1, 1, 1), (1, 1, -1), (1, -1, 1), (-1, 1, 1),
                  (-1, -1, 1), (-1, 1, -1), (1, -1, -1), (-1, -1, -1))
)


TOPOLOGIES = (
    Topology("continuous", "continuous A/B electrode", (DIAGONAL,)),
    Topology("segmented", "eight independently captured segments", SEGMENTS, ports=8),
    Topology("modal3", "three modal electrode combinations", MODES, ports=3),
    Topology("lc_orthomode", "passive LC orthomode network", ROTATED_MODES,
             ports=3, reactive_elements=3),
    Topology("sshi", "self-powered SSHI on one face pair", (DIAGONAL,),
             reactive_elements=1, switches=2),
    Topology("sece", "self-sensing SECE on one face pair", (DIAGONAL,), switches=2),
    Topology("birel_sshi", "rectifierless bipolar SSHI on one face pair", (DIAGONAL,),
             reactive_elements=1, switches=2),
    Topology("mechanical_hprime", "mechanical residual-selected fresh contact", (DIAGONAL,),
             recurrence="fresh_residual", switches=1),
    Topology("second_crystal", "matched second-crystal mode converter", ROTATED_MODES,
             ports=3,
             conditional="closes only if coupling supplies three independent matched modes"),
)


SEEDS = {
    "uniform": DIAGONAL,
    "center": (0.0, 1.0, 0.0),
    "dipole": (1 / sqrt(2), 0.0, -1 / sqrt(2)),
    "curvature": (1 / sqrt(6), -2 / sqrt(6), 1 / sqrt(6)),
}


def run_topology(topology, seed, efficiency=0.999):
    if not 0.0 <= efficiency <= 1.0:
        raise ValueError("efficiency must lie in [0, 1]")
    initial = energy(seed)
    residual = list(seed)
    applications = []
    cuts = orthogonal_basis(topology.cuts)
    if topology.recurrence == "fresh_residual":
        cuts = cuts[:1]

    for cut in cuts:
        amplitude = dot(cut, residual)
        projection = scale(amplitude, cut)
        projected = energy(projection)
        residual = subtract(residual, projection)
        if projected > TOLERANCE or topology.recurrence == "fresh_residual":
            applications.append({"cut": cut, "P": projected,
                                 "q_minus_sigma": energy(residual)})

    if topology.recurrence == "fresh_residual" and energy(residual) > TOLERANCE:
        fresh = unit(residual)
        projected = energy(residual)
        residual = [0.0, 0.0, 0.0]
        applications.append({"cut": fresh, "P": projected,
                             "q_minus_sigma": 0.0})

    captured = sum(item["P"] for item in applications)
    held = efficiency * captured
    loss = (1.0 - efficiency) * captured
    remaining = energy(residual)
    return {
        "seed": seed,
        "initial_energy": initial,
        "applications": applications,
        "observed_rank": len(orthogonal_basis(topology.cuts)),
        "captured_fraction": captured / initial if initial else 0.0,
        "held_fraction": held / initial if initial else 0.0,
        "loss_fraction": loss / initial if initial else 0.0,
        "residual_fraction": remaining / initial if initial else 0.0,
        "closure_residual": held + loss + remaining - initial,
    }


def run_tournament(efficiency=0.999):
    results = []
    for topology in TOPOLOGIES:
        trials = {name: run_topology(topology, seed, efficiency)
                  for name, seed in SEEDS.items()}
        results.append({
            "key": topology.key,
            "label": topology.label,
            "mechanism": topology.recurrence,
            "ports": topology.ports,
            "reactive_elements": topology.reactive_elements,
            "switches": topology.switches,
            "conditional": topology.conditional,
            "worst_capture": min(trial["captured_fraction"] for trial in trials.values()),
            "mean_capture": sum(trial["captured_fraction"] for trial in trials.values()) / len(trials),
            "max_applications": max(len(trial["applications"]) for trial in trials.values()),
            "trials": trials,
        })
    return {
        "epistemic_status": (
            "dimension-free linear observability tournament; topology is compared, not quartz "
            "power, resonance, component loss, or build yield"
        ),
        "common_efficiency": efficiency,
        "source_work": 0.0,
        "results": results,
        "q_minus_sigma": (
            "Topologies with the same observed rank are indistinguishable here; measured axis, "
            "modal coupling, thresholds, parasitics, and loading are the next physical cut."
        ),
    }
