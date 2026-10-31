"""Reduced quartz, acoustic-field, and speaker-return engine."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
import csv
import json
from typing import Any

from native import matrix as nm

Vector = list[float]


@dataclass(frozen=True)
class AcousticParameters:
    quartz_mass: tuple[float, float, float] = (1.0, 1.1, 0.9)
    quartz_stiffness: tuple[float, float, float] = (1.0, 1.25, 0.85)
    capacitance: tuple[float, float, float] = (1.0, 0.95, 1.05)
    piezo_coupling: tuple[tuple[float, float, float], ...] = (
        (0.00, 0.16, -0.11), (0.16, 0.00, 0.13), (-0.11, 0.13, 0.00))
    acoustic_mass: float = 0.8
    acoustic_stiffness: float = 0.72
    acoustic_damping: float = 0.01
    acoustic_coupling: tuple[float, float, float] = (0.13, -0.08, 0.05)
    electrical_conductance: float = 0.002
    load_conductance: float = 0.0
    speaker_gain: float = 0.0
    fixed_feedback_cut: int | None = None
    selection_mode: str = "residual"
    random_seed: int = 1729
    step: float = 0.02


@dataclass
class AcousticState:
    x: Vector
    velocity: Vector
    voltage: Vector
    acoustic_displacement: float
    acoustic_velocity: float

    def vector(self) -> Vector:
        return [*self.x, *self.velocity, *self.voltage,
                self.acoustic_displacement, self.acoustic_velocity]

    @classmethod
    def from_vector(cls, values: Vector) -> "AcousticState":
        return cls(list(values[0:3]), list(values[3:6]), list(values[6:9]),
                   float(values[9]), float(values[10]))


@dataclass
class AcousticAccrual:
    applications: list[dict[str, Any]] = field(default_factory=list)
    count: list[int] = field(default_factory=lambda: [0, 0, 0])
    mean_voltage: Vector = field(default_factory=lambda: [0.0, 0.0, 0.0])
    supplied_work: float = 0.0
    internal_electrical_loss: float = 0.0
    acoustic_loss: float = 0.0
    delivered_load_work: float = 0.0


class AcousticQuartzBody:
    """Eleven-state reciprocal quartz/acoustic body with speaker return."""

    def __init__(self, params: AcousticParameters):
        if params.step <= 0.0:
            raise ValueError("step must be positive")
        if params.acoustic_mass <= 0.0 or params.acoustic_stiffness <= 0.0:
            raise ValueError("acoustic mass and stiffness must be positive")
        if params.fixed_feedback_cut not in (None, 0, 1, 2):
            raise ValueError("fixed feedback cut must be 0, 1, 2, or None")
        if params.selection_mode not in ("residual", "round_robin", "random"):
            raise ValueError("selection mode must be residual, round_robin, or random")
        self.params = params
        self.M = nm.diagonal(params.quartz_mass)
        self.K = nm.diagonal(params.quartz_stiffness)
        self.C = nm.diagonal(params.capacitance)
        self.theta = nm.matrix(params.piezo_coupling)
        self.b = list(params.acoustic_coupling)
        self._transitions: dict[int, list[list[float]]] = {}

    def _matrix(self, cut: int):
        p = self.params
        rows = nm.zeros(11, 11)
        minv = nm.inverse_diagonal(p.quartz_mass)
        cinv = nm.inverse_diagonal(p.capacitance)
        mechanical = nm.scale(-1.0, nm.multiply(minv, self.K))
        converse = nm.scale(-1.0, nm.multiply(minv, self.theta))
        direct = nm.multiply(cinv, nm.transpose(self.theta))
        total_conductance = p.electrical_conductance + p.load_conductance
        leakage = nm.diagonal(tuple(-total_conductance / c for c in p.capacitance))
        for r in range(3):
            rows[r][3 + r] = 1.0
            for c in range(3):
                rows[3 + r][c] = mechanical[r][c]
                rows[3 + r][6 + c] = converse[r][c]
                rows[6 + r][3 + c] = direct[r][c]
                rows[6 + r][6 + c] = leakage[r][c]
            rows[3 + r][9] = self.b[r] / p.quartz_mass[r]
        rows[9][10] = 1.0
        for c in range(3):
            rows[10][c] = self.b[c] / p.acoustic_mass
        rows[10][9] = -p.acoustic_stiffness / p.acoustic_mass
        rows[10][10] = -p.acoustic_damping / p.acoustic_mass
        rows[10][6 + cut] += p.speaker_gain / p.acoustic_mass
        return rows

    def step(self, state: AcousticState, cut: int) -> AcousticState:
        # With no speaker return the cut cannot alter the physical matrix. Keeping one
        # transition makes that independence structural rather than merely numerical.
        key = cut if self.params.speaker_gain != 0.0 else 0
        transition = self._transitions.get(key)
        if transition is None:
            a = self._matrix(key)
            eye = nm.identity(11)
            half = nm.scale(self.params.step / 2.0, a)
            transition = nm.solve(nm.subtract(eye, half), nm.add(eye, half))
            self._transitions[key] = transition
        return AcousticState.from_vector(nm.matvec(transition, state.vector()))

    def stored_energy(self, state: AcousticState) -> float:
        p = self.params
        quartz = 0.5 * (nm.dot(state.velocity, nm.matvec(self.M, state.velocity))
                        + nm.dot(state.x, nm.matvec(self.K, state.x))
                        + nm.dot(state.voltage, nm.matvec(self.C, state.voltage)))
        acoustic = 0.5 * (p.acoustic_mass * state.acoustic_velocity ** 2
                          + p.acoustic_stiffness * state.acoustic_displacement ** 2)
        return quartz + acoustic - state.acoustic_displacement * nm.dot(self.b, state.x)

    def source_power(self, state: AcousticState, cut: int) -> float:
        return self.params.speaker_gain * state.voltage[cut] * state.acoustic_velocity

    def electrical_loss_power(self, state: AcousticState) -> float:
        return self.params.electrical_conductance * nm.dot(state.voltage, state.voltage)

    def load_power(self, state: AcousticState) -> float:
        return self.params.load_conductance * nm.dot(state.voltage, state.voltage)

    def acoustic_loss_power(self, state: AcousticState) -> float:
        return self.params.acoustic_damping * state.acoustic_velocity ** 2

    def dissipation_power(self, state: AcousticState) -> float:
        return (self.electrical_loss_power(state) + self.load_power(state)
                + self.acoustic_loss_power(state))


class AcousticEngine:
    def __init__(self, body: AcousticQuartzBody):
        self.body = body
        self.accrual = AcousticAccrual()

    def _select_cut(self, voltage: Vector, beat: int) -> int:
        fixed = self.body.params.fixed_feedback_cut
        if fixed is not None:
            return fixed
        if self.body.params.selection_mode == "round_robin":
            return (beat - 1) % 3
        if self.body.params.selection_mode == "random":
            # Stateless deterministic control, reproducible across runs.
            value = (1103515245 * (beat + self.body.params.random_seed) + 12345) & 0x7fffffff
            return value % 3
        residual = [v - mean for v, mean in zip(voltage, self.accrual.mean_voltage)]
        largest = max(abs(value) for value in residual)
        candidates = [i for i, value in enumerate(residual) if abs(value) == largest]
        if self.accrual.applications:
            previous = int(self.accrual.applications[-1]["h"])
            for candidate in candidates:
                if candidate != previous:
                    return candidate
        return candidates[0]

    def apply(self, state: AcousticState, beat: int):
        h = self._select_cut(state.voltage, beat)
        before = self.body.stored_energy(state)
        source_before = self.body.source_power(state, h)
        electrical_before = self.body.electrical_loss_power(state)
        acoustic_before = self.body.acoustic_loss_power(state)
        load_before = self.body.load_power(state)
        received = self.body.step(state, h)
        source_after = self.body.source_power(received, h)
        electrical_after = self.body.electrical_loss_power(received)
        acoustic_after = self.body.acoustic_loss_power(received)
        load_after = self.body.load_power(received)
        dt = self.body.params.step
        source_work = 0.5 * dt * (source_before + source_after)
        electrical_loss = max(0.0, 0.5 * dt * (electrical_before + electrical_after))
        acoustic_loss = max(0.0, 0.5 * dt * (acoustic_before + acoustic_after))
        load_work = max(0.0, 0.5 * dt * (load_before + load_after))
        self.accrual.supplied_work += source_work
        self.accrual.internal_electrical_loss += electrical_loss
        self.accrual.acoustic_loss += acoustic_loss
        self.accrual.delivered_load_work += load_work
        sigma = float(received.voltage[h])
        projection = float(self.accrual.mean_voltage[h])
        residual = sigma - projection
        n = self.accrual.count[h] + 1
        self.accrual.count[h] = n
        self.accrual.mean_voltage[h] += residual / n
        application = {
            "beat": beat, "h": h, "h_forced_from": "current_voltage_residual",
            "P": projection, "sigma": sigma, "q_minus_sigma": residual,
            "Lambda_plus": len(self.accrual.applications) + 1,
            "acoustic_displacement": received.acoustic_displacement,
            "acoustic_velocity": received.acoustic_velocity,
            "speaker_drive": self.body.params.speaker_gain * received.voltage[h],
            "physical": {"stored_before": before, "stored_after": self.body.stored_energy(received),
                         "source_work_step": source_work,
                         "internal_electrical_loss_step": electrical_loss,
                         "acoustic_loss_step": acoustic_loss,
                         "delivered_load_work_step": load_work}}
        self.accrual.applications.append(application)
        return received, application

    def run(self, initial: AcousticState, beats: int):
        states, applications, state = [initial], [], initial
        for beat in range(1, beats + 1):
            state, application = self.apply(state, beat)
            states.append(state)
            applications.append(application)
        return states, applications

    def summary(self):
        latest = self.accrual.applications[-1] if self.accrual.applications else None
        return {
            "triple": {"P": None if latest is None else latest["P"],
                       "q_minus_sigma": None if latest is None else latest["q_minus_sigma"],
                       "Lambda_plus": len(self.accrual.applications)},
            "projection_by_cut": list(self.accrual.mean_voltage),
            "applications_by_cut": list(self.accrual.count),
            "source_work": self.accrual.supplied_work,
            "internal_electrical_loss": self.accrual.internal_electrical_loss,
            "acoustic_loss": self.accrual.acoustic_loss,
            "delivered_load_work": self.accrual.delivered_load_work,
            "dissipated": (self.accrual.internal_electrical_loss
                           + self.accrual.acoustic_loss
                           + self.accrual.delivered_load_work),
            "epistemic_status": "normalized reduced-order model; not fitted to crystal axes or speaker"}


def initial_acoustic_state(compression: float = 1.0, acoustic_seed: float = 0.0):
    return AcousticState([compression, 0.0, 0.0], [0.0] * 3, [0.0] * 3,
                         acoustic_seed, 0.0)


def write_acoustic_run(directory: Path, params: AcousticParameters, body: AcousticQuartzBody,
                       engine: AcousticEngine, states: list[AcousticState], applications):
    directory.mkdir(parents=True, exist_ok=False)
    with (directory / "trace.jsonl").open("w", encoding="utf-8") as handle:
        for application in applications:
            handle.write(json.dumps(application, sort_keys=True) + "\n")
    with (directory / "state.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(("beat", "x0", "x1", "x2", "v0", "v1", "v2", "V0", "V1", "V2",
                         "acoustic_x", "acoustic_v", "stored_energy"))
        for beat, state in enumerate(states):
            writer.writerow((beat, *state.x, *state.velocity, *state.voltage,
                             state.acoustic_displacement, state.acoustic_velocity,
                             body.stored_energy(state)))
    payload = {"parameters": asdict(params), **engine.summary()}
    (directory / "summary.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n",
                                             encoding="utf-8")
