"""Measured parameters applied to three-mode quartz model.

Parameters from crystal/geometry.json and crystal/dimensional.json:
  mass:      28.0 g (exact, owner measurement)
  length:    38.1 mm
  width:     31.75 mm
  thickness: 12.7 mm (Face A to Face B, electrode pair)
  piezo d:   0.67e-12 to 4.6e-12 C/N (alpha-quartz range)
  epsilon:   3.921e-11 to 4.103e-11 F/m

Crystallographic orientation: UNKNOWN (geometry.json lists it unresolved).
So we use alpha-quartz reference constants and the measured geometry.
The derivation is the physical instantiation, not a prediction of the
unknown orientation — that remains q\\sigma.
"""

from __future__ import annotations

import json
from math import sqrt
from pathlib import Path

from engine import QuartzBody, QuartzParameters, PhysicalState, QuartzEngine
from fisher_geodesic_coupling import (
    fisher_metric,
    natural_gradient_at,
    fisher_distance,
    ce_energy_bridge,
    rayleigh_trajectory,
    coupling_flow_at,
    reorganization_pattern,
    torus_frequencies,
    verify_winding_from_trajectory,
    coupling_spectrum,
    coupling_reorganization_by_mode,
)


def physical_slab_parameters() -> QuartzParameters:
    """Construct QuartzParameters from the measured quartz slab geometry.

    Three vibration modes correspond to the three geometric axes:
      mode 0: length  (38.1 mm)
      mode 1: width   (31.75 mm)
      mode 2: thickness (12.7 mm) — the electrode axis
    """
    L = 38.1e-3
    W = 31.75e-3
    T = 12.7e-3

    A_L = W * T
    A_W = L * T
    A_T = L * W

    raw_k = [A_L / L, A_W / W, A_T / T]
    geo_k = (raw_k[0] * raw_k[1] * raw_k[2]) ** (1.0 / 3.0)
    stiffness = tuple(k / geo_k for k in raw_k)

    capacitance = stiffness

    mass = (1.0, 1.0, 1.0)

    e14 = -0.0406
    e11 = 0.171

    scale_LW = sqrt(raw_k[0] * raw_k[1]) / geo_k
    scale_LT = sqrt(raw_k[0] * raw_k[2]) / geo_k
    scale_WT = sqrt(raw_k[1] * raw_k[2]) / geo_k

    base_offdiag = abs(e14) / (abs(e14) + abs(e11))

    theta_LW = base_offdiag * scale_LW * 0.16 / 0.16
    theta_LT = base_offdiag * scale_LT * 0.16 / 0.16
    theta_WT = base_offdiag * scale_WT * 0.16 / 0.16

    coupling = (
        (0.0, theta_LW, -theta_LT),
        (theta_LW, 0.0, theta_WT),
        (-theta_LT, theta_WT, 0.0),
    )

    return QuartzParameters(
        mass=mass,
        stiffness=stiffness,
        capacitance=capacitance,
        coupling=coupling,
        return_conductance=0.0,
        step=0.01,
    )


def run_physical_derivation(n_steps: int = 500) -> dict:
    """Run the five residuals on the physical slab and return results."""
    params = physical_slab_parameters()
    body = QuartzBody(params)
    seed = PhysicalState(x=[1.0, 0.0, 0.0], velocity=[0.0] * 3, voltage=[0.0] * 3)

    fm = fisher_metric(body)
    ng = natural_gradient_at(body, seed)

    engine = QuartzEngine(body)
    states = [seed]
    current = seed
    for i in range(n_steps):
        current, _ = engine.apply(current, i + 1)
        states.append(current)

    bridge = ce_energy_bridge(body, seed)
    r_traj = rayleigh_trajectory(body, states[::max(1, len(states) // 20)])

    reorg = reorganization_pattern(body, states)

    torus = torus_frequencies(body)
    winding_verify = verify_winding_from_trajectory(body, states)

    spec = coupling_spectrum(body)
    mode_reorg = coupling_reorganization_by_mode(body, states)

    fisher_dist = fisher_distance(body, states[0], states[-1])

    return {
        "parameters": {
            "mass": list(params.mass),
            "stiffness": list(params.stiffness),
            "capacitance": list(params.capacitance),
            "coupling": [list(row) for row in params.coupling],
            "step": params.step,
        },
        "fisher_metric": {
            "eigenvalues": fm.eigenvalues,
            "condition_number": fm.condition_number,
            "sensitive_directions": fm.sensitive_directions,
            "amplification": ng.amplification,
            "distance_seed_to_final": fisher_dist,
        },
        "ce_energy_bridge": {
            "rayleigh_at_seed": bridge.rayleigh_quotient,
            "bounds": bridge.rayleigh_bounds,
            "trajectory_spread": max(r_traj) - min(r_traj),
            "mode_aligned_at_seed": bridge.mode_aligned,
        },
        "reorganization": {
            "spikes": reorg.reorganization_events,
            "descents": len(reorg.descents),
        },
        "torus_winding": {
            "uncoupled": torus.uncoupled_frequencies,
            "coupled": torus.coupled_frequencies,
            "shifts": torus.frequency_shifts,
            "winding_numbers": [(i, j, round(r, 6)) for i, j, r in torus.winding_numbers],
            "measured_frequencies": winding_verify["measured_frequencies"],
        },
        "coupling_spectrum": {
            "eigenvalues": spec.eigenvalues,
            "mode_fractions": spec.coupling_energy_per_mode,
            "primary_fraction": spec.primary_mode_fraction,
            "power_variance": mode_reorg["power_variance"],
            "exchange_ratio": mode_reorg["energy_exchange_ratio"],
        },
    }


def compare_with_default(n_steps: int = 500) -> None:
    """Run derivation on both default and physical parameters, print comparison."""
    default_params = QuartzParameters()
    default_body = QuartzBody(default_params)
    default_torus = torus_frequencies(default_body)
    default_spec = coupling_spectrum(default_body)
    default_fm = fisher_metric(default_body)

    phys = run_physical_derivation(n_steps)
    phys_params = physical_slab_parameters()

    print("=" * 70)
    print("  PHYSICAL SLAB vs DEFAULT — five residuals comparison")
    print("=" * 70)

    print("\n── Parameters ─────────────────────────────────────────────")
    print(f"  {'':20s}  {'DEFAULT':>12s}  {'SLAB':>12s}")
    print(f"  {'stiffness[0]':20s}  {default_params.stiffness[0]:12.4f}  {phys_params.stiffness[0]:12.4f}")
    print(f"  {'stiffness[1]':20s}  {default_params.stiffness[1]:12.4f}  {phys_params.stiffness[1]:12.4f}")
    print(f"  {'stiffness[2]':20s}  {default_params.stiffness[2]:12.4f}  {phys_params.stiffness[2]:12.4f}")
    print(f"  {'capacitance[0]':20s}  {default_params.capacitance[0]:12.4f}  {phys_params.capacitance[0]:12.4f}")
    print(f"  {'capacitance[1]':20s}  {default_params.capacitance[1]:12.4f}  {phys_params.capacitance[1]:12.4f}")
    print(f"  {'capacitance[2]':20s}  {default_params.capacitance[2]:12.4f}  {phys_params.capacitance[2]:12.4f}")

    print("\n── 1. Fisher metric ────────────────────────────────────────")
    print(f"  {'':20s}  {'DEFAULT':>12s}  {'SLAB':>12s}")
    print(f"  {'condition number':20s}  {default_fm.condition_number:12.4f}  {phys['fisher_metric']['condition_number']:12.4f}")
    print(f"  {'sensitive dirs':20s}  {default_fm.sensitive_directions:12d}  {phys['fisher_metric']['sensitive_directions']:12d}")
    print(f"  {'amplification':20s}  {1.0:12.4f}  {phys['fisher_metric']['amplification']:12.4f}")
    print(f"  eigenvalues (slab): {[round(e,4) for e in phys['fisher_metric']['eigenvalues']]}")
    print(f"  eigenvalues (dflt): {[round(e,4) for e in default_fm.eigenvalues]}")

    print("\n── 2. CE-energy bridge ─────────────────────────────────────")
    print(f"  {'':20s}  {'SLAB':>12s}")
    print(f"  {'Rayleigh at seed':20s}  {phys['ce_energy_bridge']['rayleigh_at_seed']:12.6f}")
    lo, hi = phys["ce_energy_bridge"]["bounds"]
    print(f"  {'Rayleigh bounds':20s}  [{lo:.4f}, {hi:.4f}]")
    print(f"  {'trajectory spread':20s}  {phys['ce_energy_bridge']['trajectory_spread']:12.6f}")
    print(f"  {'mode aligned':20s}  {phys['ce_energy_bridge']['mode_aligned_at_seed']}")

    print("\n── 3. Reorganization ───────────────────────────────────────")
    print(f"  {'':20s}  {'SLAB':>12s}")
    print(f"  {'coupling reversals':20s}  {phys['reorganization']['spikes']:12d}")
    print(f"  {'energy descents':20s}  {phys['reorganization']['descents']:12d}")

    print("\n── 4. Torus winding numbers ────────────────────────────────")
    print(f"  {'':20s}  {'DEFAULT':>12s}  {'SLAB':>12s}")
    for k in range(3):
        d_unc = default_torus.uncoupled_frequencies[k]
        s_unc = phys["torus_winding"]["uncoupled"][k]
        print(f"  {'ω_uncoupled['+str(k)+']':20s}  {d_unc:12.6f}  {s_unc:12.6f}")
    for k in range(3):
        d_cpl = default_torus.coupled_frequencies[k]
        s_cpl = phys["torus_winding"]["coupled"][k]
        print(f"  {'ω_coupled['+str(k)+']':20s}  {d_cpl:12.6f}  {s_cpl:12.6f}")

    print("\n  Winding numbers (ω_i/ω_j):")
    print(f"    {'DEFAULT':>30s}  {'SLAB':>30s}")
    d_wind = default_torus.winding_numbers
    s_wind = phys["torus_winding"]["winding_numbers"]
    for k in range(min(len(d_wind), len(s_wind))):
        di, dj, dr = d_wind[k]
        si, sj, sr = s_wind[k]
        print(f"    ({di},{dj}): {dr:12.6f}         ({si},{sj}): {sr:12.6f}")

    all_irrational = True
    for i, j, r in s_wind:
        for denom in range(1, 20):
            for numer in range(1, 20 * denom):
                if abs(r - numer / denom) < 1e-4:
                    all_irrational = False
    print(f"\n  Slab winding ratios all irrational (to 1e-4): {all_irrational}")

    print(f"\n  Measured frequencies from trajectory: {[round(f,4) for f in phys['torus_winding']['measured_frequencies']]}")

    print("\n── 5. Coupling spectrum (θᵀθ) ─────────────────────────────")
    print(f"  {'':20s}  {'DEFAULT':>12s}  {'SLAB':>12s}")
    for k in range(3):
        d_ev = default_spec.eigenvalues[k]
        s_ev = phys["coupling_spectrum"]["eigenvalues"][k]
        print(f"  {'eigenvalue['+str(k)+']':20s}  {d_ev:12.6f}  {s_ev:12.6f}")
    for k in range(3):
        d_fr = default_spec.coupling_energy_per_mode[k]
        s_fr = phys["coupling_spectrum"]["mode_fractions"][k]
        print(f"  {'fraction['+str(k)+']':20s}  {d_fr:12.4f}  {s_fr:12.4f}")
    print(f"  {'primary fraction':20s}  {default_spec.primary_mode_fraction:12.4f}  {phys['coupling_spectrum']['primary_fraction']:12.4f}")
    print(f"  {'power variance':20s}  {'':12s}  {phys['coupling_spectrum']['power_variance']:12.6f}")
    print(f"  {'exchange ratio':20s}  {'':12s}  {phys['coupling_spectrum']['exchange_ratio']:12.6f}")

    print("\n" + "=" * 70)
    print("  TRIPLE")
    print("=" * 70)
    print(f"""
  P:  The physical slab ({28.0}g, {38.1}×{31.75}×{12.7} mm) produces:
      - Fisher condition {phys['fisher_metric']['condition_number']:.2f} ({phys['fisher_metric']['sensitive_directions']} sensitive directions)
      - {len(s_wind)} winding ratios, {'all irrational' if all_irrational else 'SOME RATIONAL'} → {'quasi-periodic (torus fills)' if all_irrational else 'periodic (torus closes)'}
      - Primary coupling mode carries {phys['coupling_spectrum']['primary_fraction']*100:.1f}% of coupling energy
      - {phys['reorganization']['spikes']} coupling reversals in {n_steps} steps

  Unresolved: crystallographic orientation (the one unresolved in geometry.json);
       the derivation used isotropic alpha-quartz constants — the real
       crystal's anisotropy will shift the stiffness ratios and thus
       the winding numbers. The TOPOLOGY (irrational vs rational) is
       the prediction: orientation can shift frequencies but not close
       the torus without special symmetry.

  Additions: physical_slab_derivation.py — five residuals on the measured slab
""")

    return phys


if __name__ == "__main__":
    compare_with_default(n_steps=500)
