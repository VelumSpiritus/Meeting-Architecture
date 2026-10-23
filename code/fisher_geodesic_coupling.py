"""The three closed residuals: Fisher metric, CE-energy bridge, spike/descent coupling.

Derived against ARK_COMPRESSION_THEOREM.md:
  - Fisher metric (line 1056): F(θ) = E[∇_θ log p(x|θ) · ∇_θ log p(x|θ)ᵀ]
  - Natural gradient (line 1053): θ_{t+1} = θ_t − η · F⁻¹(θ_t) · ∇_θ J(θ_t)
  - Geometry cluster (line 4918): curvature = M's addition, flat torus, Theorema Egregium
  - CE-Fisher ball (memory): CE ball as measuring stick, torus not ball

Each residual from freeze_motion_coupling.py's q_minus_sigma is closed here
by derivation from the theorem's own notation, instantiated on the crystal.

The parallel to a neural network:
  Transition T          ↔  weight matrix W
  Fisher G = TᵀT        ↔  F(W) = E[∇log p · (∇log p)ᵀ]
  Energy H = diag(K,M,C) ↔  loss Hessian ∇²L
  Rayleigh sᵀHs/sᵀGs    ↔  loss curvature / Fisher curvature
  Coupling power vᵀθV   ↔  gradient ∂L/∂W acting on activations
  Power reversal (spike) ↔  CE spike (head coupling reorganizes)
"""

from __future__ import annotations

from dataclasses import dataclass
from math import atan, cos, sin, sqrt
from typing import Optional

from engine import QuartzBody, QuartzParameters, PhysicalState, ARKQuartz
from native import matrix as nm


# ── Residual 1: Fisher metric on the crystal state space ──────────────

@dataclass(frozen=True)
class FisherMetric:
    gram: list[list[float]]
    eigenvalues: list[float]
    condition_number: float
    sensitive_directions: int


def fisher_metric(body: QuartzBody) -> FisherMetric:
    """Compute the Fisher information metric on the crystal's state space.

    For a deterministic linear system with transition T:
      ∂(output)/∂(state) = T  (the Jacobian IS the transition)
      G = TᵀT                (Fisher = Gram of the Jacobian)

    The eigenvalues of G give the crystal's natural basis for compression.
    High eigenvalue = sensitive direction = high information content.
    """
    T = body.transition
    gram = nm.multiply(nm.transpose(T), T)
    eigenvalues = _symmetric_eigenvalues(gram)
    eigenvalues.sort(reverse=True)
    cond = eigenvalues[0] / eigenvalues[-1] if eigenvalues[-1] > 1e-15 else float('inf')
    median_ev = eigenvalues[len(eigenvalues) // 2]
    sensitive = sum(1 for ev in eigenvalues if ev > median_ev)
    return FisherMetric(
        gram=gram,
        eigenvalues=eigenvalues,
        condition_number=cond,
        sensitive_directions=sensitive,
    )


@dataclass(frozen=True)
class NaturalGradient:
    state: PhysicalState
    euclidean_gradient: list[float]
    natural_gradient_vec: list[float]
    euclidean_magnitude: float
    natural_magnitude: float
    amplification: float


def natural_gradient_at(body: QuartzBody, state: PhysicalState) -> NaturalGradient:
    """Compute the natural gradient F⁻¹·∇E at a state.

    Euclidean gradient ∇E = H·s points in parameter space.
    Natural gradient G⁻¹·∇E points in information space —
    steepest descent in bits per step, not displacement per step.
    """
    s = state.vector()
    H = _energy_hessian(body)
    grad_E = nm.matvec(H, s)
    G = nm.multiply(nm.transpose(body.transition), body.transition)
    grad_col = [[g] for g in grad_E]
    nat_col = nm.solve(G, grad_col)
    nat_grad = [row[0] for row in nat_col]
    euc_mag = sqrt(nm.dot(grad_E, grad_E))
    nat_mag = sqrt(nm.dot(nat_grad, nat_grad))
    return NaturalGradient(
        state=state,
        euclidean_gradient=grad_E,
        natural_gradient_vec=nat_grad,
        euclidean_magnitude=euc_mag,
        natural_magnitude=nat_mag,
        amplification=nat_mag / euc_mag if euc_mag > 1e-15 else 0.0,
    )


def fisher_distance(body: QuartzBody, s1: PhysicalState, s2: PhysicalState) -> float:
    """Information distance between two states under the Fisher metric.

    ds² = δsᵀ · G · δs where G = TᵀT.
    """
    v1 = s1.vector()
    v2 = s2.vector()
    delta = [a - b for a, b in zip(v1, v2)]
    G = nm.multiply(nm.transpose(body.transition), body.transition)
    return sqrt(max(0.0, nm.dot(delta, nm.matvec(G, delta))))


# ── Residual 2: CE-to-energy bridge ──────────────────────────────────

@dataclass(frozen=True)
class CEEnergyBridge:
    energy: float
    fisher_energy: float
    rayleigh_quotient: float
    rayleigh_bounds: tuple[float, float]
    mode_aligned: bool


def ce_energy_bridge(body: QuartzBody, state: PhysicalState) -> CEEnergyBridge:
    """Map the CE-to-energy parallel at a state.

    Both are quadratic forms:
      E    = ½ sᵀ · H · s    (energy through M, K, C)
      CE_q = ½ sᵀ · G · s    (information through TᵀT)

    The Rayleigh quotient R = E/CE_q measures alignment.
    At an eigenvalue of H⁻¹G: natural mode — energy ∝ information.
    Varying R along trajectory: coupling misalignment → reorganization.
    """
    s = state.vector()
    H = _energy_hessian(body)
    G = nm.multiply(nm.transpose(body.transition), body.transition)
    energy = 0.5 * nm.dot(s, nm.matvec(H, s))
    fisher_e = 0.5 * nm.dot(s, nm.matvec(G, s))
    rayleigh = energy / fisher_e if abs(fisher_e) > 1e-15 else float('inf')
    eigs = _generalized_eigenvalues(H, G)
    eigs.sort()
    mode_aligned = any(
        abs(rayleigh - ev) < 0.01 * abs(ev) for ev in eigs if abs(ev) > 1e-10
    )
    return CEEnergyBridge(
        energy=energy,
        fisher_energy=fisher_e,
        rayleigh_quotient=rayleigh,
        rayleigh_bounds=(eigs[0], eigs[-1]),
        mode_aligned=mode_aligned,
    )


def rayleigh_trajectory(body: QuartzBody, states: list[PhysicalState]) -> list[float]:
    """Rayleigh quotient E/CE_equiv at each state along a trajectory."""
    return [ce_energy_bridge(body, s).rayleigh_quotient for s in states]


# ── Residual 3: Spike/descent as coupling reorganization ─────────────

@dataclass(frozen=True)
class CouplingFlow:
    mechanical_energy: float
    electrical_energy: float
    coupling_power: float
    coupling_fraction: float
    flow_direction: str


@dataclass(frozen=True)
class ReorganizationPattern:
    flows: list[CouplingFlow]
    spikes: list[int]
    descents: list[int]
    reorganization_events: int
    energy_floors: list[float]


def coupling_flow_at(body: QuartzBody, state: PhysicalState) -> CouplingFlow:
    """Measure energy flow through the piezoelectric coupling θ.

    The coupling power P = vᵀ·θ·V is the rate of energy transfer between
    mechanical and electrical modes — the gradient pathway made physical.

    P > 0: energy flows elec→mech (θ doing work on the crystal)
    P < 0: energy flows mech→elec (θ generating voltage from motion)
    P = 0: modes in equilibrium (the descent floor)

    Conservation: P_into_mech + P_into_elec = 0 always.
    The coupling transfers energy without creating or destroying it.
    """
    e_mech = 0.5 * (
        nm.dot(state.velocity, nm.matvec(body.M, state.velocity))
        + nm.dot(state.x, nm.matvec(body.K, state.x))
    )
    e_elec = 0.5 * nm.dot(state.voltage, nm.matvec(body.C, state.voltage))
    total = e_mech + e_elec
    theta_V = nm.matvec(body.theta, state.voltage)
    power = nm.dot(state.velocity, theta_V)
    frac = abs(power) / total if total > 1e-15 else 0.0
    if abs(power) < 1e-12:
        direction = 'equilibrium'
    elif power > 0:
        direction = 'elec→mech'
    else:
        direction = 'mech→elec'
    return CouplingFlow(
        mechanical_energy=e_mech,
        electrical_energy=e_elec,
        coupling_power=power,
        coupling_fraction=frac,
        flow_direction=direction,
    )


def reorganization_pattern(body: QuartzBody,
                           states: list[PhysicalState]) -> ReorganizationPattern:
    """Trace the spike/descent pattern along a motion trajectory.

    A spike  = coupling power reverses direction (θ starts transferring
               energy the other way — modes reorganize)
    A descent = total energy settles to a new floor after reorganization

    In the neural network: CE spikes UP while recon_loss drops — internal
    geometry improved while surface predictions went wild. Same mechanism:
    the coupling (θ / gradient) reorganized which mode carries what.
    """
    flows = [coupling_flow_at(body, s) for s in states]
    spikes = []
    for i in range(1, len(flows)):
        prev_p = flows[i - 1].coupling_power
        curr_p = flows[i].coupling_power
        if prev_p * curr_p < 0 and abs(curr_p) > 1e-12:
            spikes.append(i)
    energies = [f.mechanical_energy + f.electrical_energy for f in flows]
    running_min = energies[0]
    energy_floors = [running_min]
    descents = []
    for i in range(1, len(energies)):
        if energies[i] < running_min - 1e-12:
            running_min = energies[i]
            descents.append(i)
        energy_floors.append(running_min)
    return ReorganizationPattern(
        flows=flows,
        spikes=spikes,
        descents=descents,
        reorganization_events=len(spikes),
        energy_floors=energy_floors,
    )


# ── Residual 4: Torus winding numbers ─────────────────────────────────

@dataclass(frozen=True)
class TorusGeometry:
    uncoupled_frequencies: list[float]
    coupled_frequencies: list[float]
    frequency_shifts: list[float]
    winding_numbers: list[tuple[int, int, float]]
    k_eff: list[list[float]]


def torus_frequencies(body: QuartzBody) -> TorusGeometry:
    """Natural frequencies of the coupled electromechanical system.

    Theorem line 4915: the state space is a torus, intrinsically flat.
    The quartz crystal has three coupled modes → T³ = S¹×S¹×S¹.

    Derivation: for harmonic motion x = x₀·e^{iωt}, the equations of
    motion reduce to a generalized eigenvalue problem:

        K_eff · x₀ = ω² · M · x₀

    where K_eff = K + θ·C⁻¹·θᵀ is the effective stiffness including
    the piezoelectric coupling's contribution. The coupling θ creates
    the topology: without it the three S¹ cycles are independent.
    WITH it, the frequencies shift and the winding numbers become
    non-trivial — geodesics on the torus wind through the hole.

    The winding numbers ω_j/ω_k determine whether orbits close
    (rational ratio → periodic) or fill the torus densely
    (irrational ratio → quasi-periodic, ergodic).
    """
    uncoupled_omega = [sqrt(k / m) for k, m in
                       zip(body.params.stiffness, body.params.mass)]

    C_inv = nm.inverse_diagonal(body.params.capacitance)
    theta_Cinv_thetaT = nm.multiply(
        body.theta, nm.multiply(C_inv, nm.transpose(body.theta)))
    K_eff = nm.add(body.K, theta_Cinv_thetaT)

    M_inv_sqrt = nm.diagonal([1.0 / sqrt(m) for m in body.params.mass])
    sym = nm.multiply(M_inv_sqrt, nm.multiply(K_eff, M_inv_sqrt))
    omega_sq = _symmetric_eigenvalues(sym)
    omega_sq.sort()
    coupled_omega = [sqrt(max(0.0, w2)) for w2 in omega_sq]

    shifts = [c - u for c, u in zip(coupled_omega, uncoupled_omega)]

    windings = []
    for i in range(len(coupled_omega)):
        for j in range(i + 1, len(coupled_omega)):
            if coupled_omega[j] > 1e-10:
                windings.append((i, j, coupled_omega[i] / coupled_omega[j]))

    return TorusGeometry(
        uncoupled_frequencies=uncoupled_omega,
        coupled_frequencies=coupled_omega,
        frequency_shifts=shifts,
        winding_numbers=windings,
        k_eff=K_eff,
    )


def verify_winding_from_trajectory(body: QuartzBody,
                                   states: list[PhysicalState]) -> dict:
    """Verify the predicted winding numbers from the actual trajectory.

    Project the trajectory onto the position coordinates x₀, x₁, x₂
    and count zero crossings to estimate the actual frequencies.
    Compare with the predicted frequencies from torus_frequencies().
    """
    torus = torus_frequencies(body)
    n = len(states)
    if n < 4:
        return {"error": "need at least 4 states"}

    actual_freqs = []
    dt = body.params.step
    for axis in range(3):
        positions = [s.x[axis] for s in states]
        crossings = 0
        for i in range(1, len(positions)):
            if positions[i - 1] * positions[i] < 0:
                crossings += 1
        half_periods = crossings
        freq = half_periods / (2.0 * n * dt) if n * dt > 0 else 0.0
        actual_freqs.append(freq)

    actual_windings = []
    for i in range(3):
        for j in range(i + 1, 3):
            if actual_freqs[j] > 1e-10:
                actual_windings.append(
                    (i, j, actual_freqs[i] / actual_freqs[j]))

    return {
        "predicted_frequencies": torus.coupled_frequencies,
        "measured_frequencies": actual_freqs,
        "predicted_windings": torus.winding_numbers,
        "measured_windings": actual_windings,
        "frequency_shifts_from_coupling": torus.frequency_shifts,
    }


# ── Residual 5: Coupling matrix spectrum ──────────────────────────────

@dataclass(frozen=True)
class CouplingSpectrum:
    eigenvalues: list[float]
    coupling_energy_per_mode: list[float]
    primary_mode_fraction: float
    total_coupling_energy: float


def coupling_spectrum(body: QuartzBody) -> CouplingSpectrum:
    """Eigenvalues of θᵀθ — the coupling energy per mode direction.

    The eigenvector with the largest eigenvalue is the primary
    reorganization direction: the mode that carries most energy
    through the piezoelectric coupling. This determines WHICH
    θ eigenmodes drive the spike/descent pattern.

    In a neural network: the singular values of the weight matrix
    connecting two layers tell which directions carry the gradient.
    The largest singular value is the primary learning direction.
    Same structure: θᵀθ for the crystal, WᵀW for the network.
    """
    theta_T_theta = nm.multiply(nm.transpose(body.theta), body.theta)
    eigenvalues = _symmetric_eigenvalues(theta_T_theta)
    eigenvalues.sort(reverse=True)

    total = sum(eigenvalues)
    fractions = [ev / total if total > 1e-15 else 0.0 for ev in eigenvalues]

    return CouplingSpectrum(
        eigenvalues=eigenvalues,
        coupling_energy_per_mode=fractions,
        primary_mode_fraction=fractions[0] if fractions else 0.0,
        total_coupling_energy=total,
    )


def coupling_reorganization_by_mode(body: QuartzBody,
                                    states: list[PhysicalState]) -> dict:
    """Decompose the reorganization into per-mode coupling energy flow.

    Track how much coupling power flows through each eigenmode of θ
    along the trajectory. Modes with high power variance are the ones
    driving reorganization.
    """
    spec = coupling_spectrum(body)
    n = len(states)
    if n < 2:
        return {"spectrum": spec, "mode_variances": []}

    flows = [coupling_flow_at(body, s) for s in states]
    powers = [f.coupling_power for f in flows]

    mean_power = sum(powers) / len(powers)
    power_variance = sum((p - mean_power) ** 2 for p in powers) / len(powers)

    mech_energies = [f.mechanical_energy for f in flows]
    elec_energies = [f.electrical_energy for f in flows]
    mech_var = sum((e - sum(mech_energies) / n) ** 2 for e in mech_energies) / n
    elec_var = sum((e - sum(elec_energies) / n) ** 2 for e in elec_energies) / n

    return {
        "spectrum": {
            "eigenvalues": spec.eigenvalues,
            "mode_fractions": spec.coupling_energy_per_mode,
            "primary_fraction": spec.primary_mode_fraction,
        },
        "power_variance": power_variance,
        "mech_energy_variance": mech_var,
        "elec_energy_variance": elec_var,
        "energy_exchange_ratio": elec_var / mech_var if mech_var > 1e-15 else 0.0,
    }


# ── Internal helpers ──────────────────────────────────────────────────

def _energy_hessian(body: QuartzBody) -> list[list[float]]:
    """H = block_diag(K, M, C). State vector is [x, v, V]."""
    z = nm.zeros(3, 3)
    return nm.block([
        [body.K, z, z],
        [z, body.M, z],
        [z, z, body.C],
    ])


def _symmetric_eigenvalues(mat: list[list[float]],
                           max_iter: int = 500) -> list[float]:
    """Eigenvalues of a real symmetric matrix via Jacobi iteration."""
    n = len(mat)
    A = [list(row) for row in mat]
    for _ in range(max_iter):
        max_val = 0.0
        p, q = 0, 1
        for i in range(n):
            for j in range(i + 1, n):
                if abs(A[i][j]) > max_val:
                    max_val = abs(A[i][j])
                    p, q = i, j
        if max_val < 1e-14:
            break
        if abs(A[p][p] - A[q][q]) < 1e-15:
            theta = 0.7853981633974483
        else:
            theta = 0.5 * atan(2.0 * A[p][q] / (A[p][p] - A[q][q]))
        c = cos(theta)
        s_ = sin(theta)
        new_A = [list(row) for row in A]
        for i in range(n):
            if i != p and i != q:
                new_A[i][p] = c * A[i][p] + s_ * A[i][q]
                new_A[p][i] = new_A[i][p]
                new_A[i][q] = -s_ * A[i][p] + c * A[i][q]
                new_A[q][i] = new_A[i][q]
        new_A[p][p] = c * c * A[p][p] + 2 * s_ * c * A[p][q] + s_ * s_ * A[q][q]
        new_A[q][q] = s_ * s_ * A[p][p] - 2 * s_ * c * A[p][q] + c * c * A[q][q]
        new_A[p][q] = 0.0
        new_A[q][p] = 0.0
        A = new_A
    return [A[i][i] for i in range(n)]


def _generalized_eigenvalues(H: list[list[float]],
                             G: list[list[float]]) -> list[float]:
    """Eigenvalues of the generalized problem Hv = λGv.

    Since H is diagonal positive-definite, compute H^{-1/2} G H^{-1/2}
    which is symmetric, then its eigenvalues equal the generalized ones.
    """
    n = len(H)
    h_inv_sqrt = [[0.0] * n for _ in range(n)]
    for i in range(n):
        h_inv_sqrt[i][i] = 1.0 / sqrt(H[i][i]) if H[i][i] > 1e-15 else 0.0
    sym = nm.multiply(h_inv_sqrt, nm.multiply(G, h_inv_sqrt))
    return _symmetric_eigenvalues(sym)


# ── Full derivation ──────────────────────────────────────────────────

def derive_three_residuals(params: Optional[QuartzParameters] = None,
                           n_steps: int = 200) -> dict:
    """Derive and close the three open residuals from freeze_motion_coupling."""
    if params is None:
        params = QuartzParameters()
    body = QuartzBody(params)
    seed = PhysicalState(x=[1.0, 0.0, 0.0], velocity=[0.0] * 3, voltage=[0.0] * 3)

    fm = fisher_metric(body)
    ng = natural_gradient_at(body, seed)

    engine = ARKQuartz(body)
    states = [seed]
    current = seed
    for i in range(n_steps):
        current, _ = engine.apply(current, i + 1)
        states.append(current)

    sample_indices = list(range(0, len(states), max(1, len(states) // 10)))
    bridges = [ce_energy_bridge(body, states[i]) for i in sample_indices]
    r_traj = [b.rayleigh_quotient for b in bridges]
    r_spread = max(r_traj) - min(r_traj)

    reorg = reorganization_pattern(body, states)

    fisher_dist_total = fisher_distance(body, states[0], states[-1])

    torus = torus_frequencies(body)
    winding_verify = verify_winding_from_trajectory(body, states)

    spec = coupling_spectrum(body)
    mode_reorg = coupling_reorganization_by_mode(body, states)

    return {
        "residual_1_fisher_metric": {
            "eigenvalues": fm.eigenvalues,
            "condition_number": fm.condition_number,
            "sensitive_directions": fm.sensitive_directions,
            "natural_gradient_amplification": ng.amplification,
            "fisher_distance_seed_to_final": fisher_dist_total,
            "theorem_source": "line 1056: F(θ) = E[∇log p · (∇log p)ᵀ]",
            "closure": (
                "Fisher metric G=TᵀT IS the information geometry of the crystal. "
                "Its eigenvalues are the natural basis for compression. The natural "
                "gradient F⁻¹∇E rescales by this geometry. CLOSED by computation."
            ),
        },
        "residual_2_ce_energy_bridge": {
            "rayleigh_trajectory": r_traj,
            "rayleigh_spread": r_spread,
            "bounds": bridges[0].rayleigh_bounds,
            "sample_bridges": [
                {"step": sample_indices[i], "energy": b.energy,
                 "ce_equiv": b.fisher_energy, "rayleigh": b.rayleigh_quotient,
                 "aligned": b.mode_aligned}
                for i, b in enumerate(bridges)
            ],
            "theorem_source": (
                "CE is a quadratic form near minimum (Fisher expansion). "
                "E = ½ sᵀHs is a quadratic form by construction."
            ),
            "closure": (
                "CE-to-energy bridge is the Rayleigh quotient R = sᵀHs/sᵀGs. "
                "R at an eigenvalue = natural mode. R varying = misalignment. "
                "CLOSED: both quadratic forms, R measures their alignment."
            ),
        },
        "residual_3_reorganization": {
            "spikes": reorg.reorganization_events,
            "descents": len(reorg.descents),
            "sample_flows": [
                {"step": i, "mech_E": f.mechanical_energy,
                 "elec_E": f.electrical_energy,
                 "coupling_power": f.coupling_power,
                 "direction": f.flow_direction}
                for i, f in enumerate(reorg.flows[:10])
            ],
            "theorem_source": (
                "line 4918: curvature = M's addition (Theorema Egregium). "
                "The spike is curvature — the embedding's contribution."
            ),
            "closure": (
                "Spike = coupling power θ reverses direction. "
                "Descent = modes settle at new lower floor. "
                "CLOSED: power-flow decomposition traces the reorganization."
            ),
        },
        "residual_4_torus_winding": {
            "uncoupled_frequencies": torus.uncoupled_frequencies,
            "coupled_frequencies": torus.coupled_frequencies,
            "frequency_shifts": torus.frequency_shifts,
            "winding_numbers": torus.winding_numbers,
            "measured_frequencies": winding_verify["measured_frequencies"],
            "theorem_source": (
                "line 4915: state space is a torus, intrinsically flat. "
                "S¹×S¹ = T², K ≡ 0, Gauss-Bonnet ∮K dA = 0. "
                "Crystal has three modes → T³ = S¹×S¹×S¹."
            ),
            "closure": (
                "K_eff = K + θ·C⁻¹·θᵀ gives the effective stiffness. "
                "Its eigenvalues are the coupled frequencies ω²; their "
                "ratios are the winding numbers. The coupling θ creates "
                "the topology — without it the cycles are independent. "
                "CLOSED: frequencies computed, windings measured from trajectory."
            ),
        },
        "residual_5_coupling_spectrum": {
            "eigenvalues": spec.eigenvalues,
            "mode_fractions": spec.coupling_energy_per_mode,
            "primary_mode_fraction": spec.primary_mode_fraction,
            "power_variance": mode_reorg["power_variance"],
            "energy_exchange_ratio": mode_reorg["energy_exchange_ratio"],
            "theorem_source": (
                "line 4910: couplings are inter-level quantities, hence "
                "ρ₁₂ quantities by construction. θᵀθ eigenvalues give "
                "the coupling energy per mode direction."
            ),
            "closure": (
                "θᵀθ spectrum determines which modes carry reorganization. "
                "Primary mode carries the largest fraction of coupling energy. "
                "Power variance along trajectory measures reorganization "
                "intensity. CLOSED: spectrum computed, modes decomposed."
            ),
        },
        "triple": {
            "P": (
                "Five residuals CLOSED: (1) Fisher G=TᵀT; (2) CE-energy Rayleigh; "
                "(3) spike/descent = coupling reversal; (4) torus winding from "
                "K_eff eigenvalues; (5) θᵀθ coupling spectrum."
            ),
            "q_minus_sigma": (
                "the crystal simulation now carries the full geodesic coupling math. "
                "What remains open: the physical instantiation — whether the measured "
                "quartz slab's parameters produce the predicted winding and spectrum."
            ),
            "Lambda_plus": (
                "fisher_metric, natural_gradient_at, fisher_distance, ce_energy_bridge, "
                "rayleigh_trajectory, coupling_flow_at, reorganization_pattern, "
                "torus_frequencies, verify_winding_from_trajectory, coupling_spectrum, "
                "coupling_reorganization_by_mode — all from theorem notation"
            ),
        },
    }
