"""Reciprocal three-mode quartz body composed by the ARK recurrence."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
import csv
import json
from typing import Any

from native import matrix as nm


Vector = list[float]


@dataclass(frozen=True)
class QuartzParameters:
    """Normalized three-mode body; modes are not asserted physical face pairs."""

    mass: tuple[float, float, float] = (1.0, 1.1, 0.9)
    stiffness: tuple[float, float, float] = (1.0, 1.25, 0.85)
    capacitance: tuple[float, float, float] = (1.0, 0.95, 1.05)
    coupling: tuple[tuple[float, float, float], ...] = (
        (0.00, 0.16, -0.11),
        (0.16, 0.00, 0.13),
        (-0.11, 0.13, 0.00),
    )
    return_conductance: float = 0.0
    step: float = 0.04


@dataclass
class PhysicalState:
    x: Vector
    velocity: Vector
    voltage: Vector

    def vector(self) -> Vector:
        return [*self.x, *self.velocity, *self.voltage]

    @classmethod
    def from_vector(cls, values: Vector) -> "PhysicalState":
        return cls(list(values[0:3]), list(values[3:6]), list(values[6:9]))


@dataclass
class Accrual:
    applications: list[dict[str, Any]] = field(default_factory=list)
    count: list[int] = field(default_factory=lambda: [0, 0, 0])
    mean_voltage: Vector = field(default_factory=lambda: [0.0, 0.0, 0.0])


class QuartzBody:
    """One energy-derived body with a native Cayley state step."""

    def __init__(self, params: QuartzParameters):
        self.params = params
        self.M = nm.diagonal(params.mass)
        self.K = nm.diagonal(params.stiffness)
        self.C = nm.diagonal(params.capacitance)
        self.theta = nm.matrix(params.coupling)
        if len(self.theta) != 3 or any(len(row) != 3 for row in self.theta):
            raise ValueError("coupling must be 3x3")
        self.G = self._return_matrix(params.return_conductance)
        self.A = self._system_matrix()
        eye = nm.identity(9)
        half_a = nm.scale(params.step / 2.0, self.A)
        self.transition = nm.solve(nm.subtract(eye, half_a), nm.add(eye, half_a))

    @staticmethod
    def _return_matrix(conductance: float):
        return nm.scale(conductance, nm.matrix(((1, 0, -1), (0, 0, 0), (-1, 0, 1))))

    def _system_matrix(self):
        z = nm.zeros(3, 3)
        i = nm.identity(3)
        minv = nm.inverse_diagonal(self.params.mass)
        cinv = nm.inverse_diagonal(self.params.capacitance)
        return nm.block([
            [z, i, z],
            [nm.scale(-1.0, nm.multiply(minv, self.K)), z,
             nm.scale(-1.0, nm.multiply(minv, self.theta))],
            [z, nm.multiply(cinv, nm.transpose(self.theta)),
             nm.scale(-1.0, nm.multiply(cinv, self.G))],
        ])

    def step(self, state: PhysicalState) -> PhysicalState:
        return PhysicalState.from_vector(nm.matvec(self.transition, state.vector()))

    def energy(self, state: PhysicalState) -> float:
        return 0.5 * (
            nm.dot(state.velocity, nm.matvec(self.M, state.velocity))
            + nm.dot(state.x, nm.matvec(self.K, state.x))
            + nm.dot(state.voltage, nm.matvec(self.C, state.voltage))
        )

    def return_power(self, state: PhysicalState) -> float:
        return nm.dot(state.voltage, nm.matvec(self.G, state.voltage))


class ARKQuartz:
    """Run F around the physical body; never substitute one application for F."""

    def __init__(self, body: QuartzBody, tolerance: float = 1e-10):
        self.body = body
        self.tolerance = tolerance
        self.accrual = Accrual()
        self.max_unexplained_energy = 0.0
        self.refuters: list[dict[str, float | int | str]] = []

    def _select_cut(self, observed: Vector) -> int:
        residuals = (list(observed) if not self.accrual.applications else
                     [value - mean for value, mean in zip(observed, self.accrual.mean_voltage)])
        magnitudes = [abs(value) for value in residuals]
        largest = max(magnitudes)
        candidates = [index for index, value in enumerate(magnitudes) if value == largest]
        if self.accrual.applications:
            previous = int(self.accrual.applications[-1]["h"])
            for candidate in candidates:
                if candidate != previous:
                    return candidate
        return candidates[0]

    @staticmethod
    def _read_cut(state: PhysicalState, cut: int) -> float:
        return float(state.voltage[cut])

    def apply(self, state: PhysicalState, beat: int) -> tuple[PhysicalState, dict[str, Any]]:
        before = self.body.energy(state)
        received = self.body.step(state)
        after = self.body.energy(received)
        h = self._select_cut(received.voltage)
        projection = float(self.accrual.mean_voltage[h])
        sigma_1 = self._read_cut(received, h)
        sigma_2 = self._read_cut(PhysicalState.from_vector(received.vector()), h)
        rho12 = 1.0 if sigma_1 == sigma_2 else 0.0
        residual = sigma_1 - projection

        unexplained = max(0.0, after - before)
        if unexplained > self.tolerance:
            self.refuters.append({"beat": beat, "kind": "energy_created", "amount": unexplained})
        self.max_unexplained_energy = max(self.max_unexplained_energy, unexplained)

        n = self.accrual.count[h] + 1
        self.accrual.count[h] = n
        self.accrual.mean_voltage[h] += (sigma_1 - self.accrual.mean_voltage[h]) / n
        application = {
            "beat": beat, "h": h, "h_forced_from": "current_residual",
            "P": projection, "sigma": sigma_1, "q_minus_sigma": residual,
            "Lambda_plus": len(self.accrual.applications) + 1,
            "rho12": rho12, "rho3": 0 if not self.refuters else len(self.refuters),
            "energy_before": before, "energy_after": after,
            "return_power": self.body.return_power(received),
        }
        self.accrual.applications.append(application)
        return received, application

    def run(self, initial: PhysicalState, beats: int):
        states, applications, state = [initial], [], initial
        for beat in range(1, beats + 1):
            state, application = self.apply(state, beat)
            states.append(state)
            applications.append(application)
        return states, applications

    def summary(self) -> dict[str, Any]:
        latest = self.accrual.applications[-1] if self.accrual.applications else None
        return {
            "triple": {"P": None if latest is None else latest["P"],
                       "q_minus_sigma": None if latest is None else latest["q_minus_sigma"],
                       "Lambda_plus": len(self.accrual.applications)},
            "projection_by_cut": list(self.accrual.mean_voltage),
            "applications_by_cut": list(self.accrual.count),
            "rho12_all": all(a["rho12"] == 1.0 for a in self.accrual.applications),
            "rho3": self.refuters,
            "max_unexplained_energy": self.max_unexplained_energy,
        }


def initial_compression(amount: float = 1.0, axis: int = 0) -> PhysicalState:
    x = [0.0, 0.0, 0.0]
    x[axis] = amount
    return PhysicalState(x=x, velocity=[0.0] * 3, voltage=[0.0] * 3)


def write_run(directory: Path, params: QuartzParameters, body: QuartzBody,
              engine: ARKQuartz, states: list[PhysicalState], applications: list[dict[str, Any]]) -> None:
    directory.mkdir(parents=True, exist_ok=False)
    with (directory / "trace.jsonl").open("w", encoding="utf-8") as handle:
        for application in applications:
            handle.write(json.dumps(application, sort_keys=True) + "\n")
    with (directory / "state.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(("beat", "x0", "x1", "x2", "v0", "v1", "v2", "V0", "V1", "V2", "energy"))
        for beat, state in enumerate(states):
            writer.writerow((beat, *state.x, *state.velocity, *state.voltage, body.energy(state)))
    payload = {"parameters": asdict(params), **engine.summary()}
    (directory / "summary.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n",
                                             encoding="utf-8")
