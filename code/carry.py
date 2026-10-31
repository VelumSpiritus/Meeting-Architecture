"""Continuous reciprocal carry from quartz field into a storage coordinate."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from acoustic import AcousticParameters
from native import matrix as nm


@dataclass(frozen=True)
class CarryParameters:
    face_cut: int = 0
    storage_capacitance: float = 4.0
    carry_inductance: float = 1.0
    carry_resistance: float = 0.0


@dataclass
class CarryState:
    x: list[float]
    velocity: list[float]
    voltage: list[float]
    acoustic_displacement: float
    acoustic_velocity: float
    storage_voltage: float
    carry_current: float

    def vector(self):
        return [*self.x, *self.velocity, *self.voltage,
                self.acoustic_displacement, self.acoustic_velocity,
                self.storage_voltage, self.carry_current]

    @classmethod
    def from_vector(cls, values):
        return cls(list(values[0:3]), list(values[3:6]), list(values[6:9]),
                   float(values[9]), float(values[10]), float(values[11]),
                   float(values[12]))


class CarryBody:
    """Thirteen-state body; V-i-z coupling is equal, opposite, and continuous."""

    def __init__(self, body: AcousticParameters, carry: CarryParameters):
        if body.speaker_gain != 0.0 or body.load_conductance != 0.0:
            raise ValueError("carry body admits no active speaker or parallel extraction load")
        if carry.face_cut not in (0, 1, 2):
            raise ValueError("face_cut must be 0, 1, or 2")
        if carry.storage_capacitance <= 0.0 or carry.carry_inductance <= 0.0:
            raise ValueError("storage capacitance and carry inductance must be positive")
        if carry.carry_resistance < 0.0:
            raise ValueError("carry resistance must be non-negative")
        self.body = body
        self.carry = carry
        self.M = nm.diagonal(body.quartz_mass)
        self.K = nm.diagonal(body.quartz_stiffness)
        self.C = nm.diagonal(body.capacitance)
        self.theta = nm.matrix(body.piezo_coupling)
        self.b = list(body.acoustic_coupling)
        self.A = self._matrix()
        eye = nm.identity(13)
        half = nm.scale(body.step / 2.0, self.A)
        self.transition = nm.solve(nm.subtract(eye, half), nm.add(eye, half))

    def _matrix(self):
        p, c = self.body, self.carry
        rows = nm.zeros(13, 13)
        minv = nm.inverse_diagonal(p.quartz_mass)
        cinv = nm.inverse_diagonal(p.capacitance)
        mechanical = nm.scale(-1.0, nm.multiply(minv, self.K))
        converse = nm.scale(-1.0, nm.multiply(minv, self.theta))
        direct = nm.multiply(cinv, nm.transpose(self.theta))
        leakage = nm.diagonal(tuple(-p.electrical_conductance / cap
                                    for cap in p.capacitance))
        for r in range(3):
            rows[r][3 + r] = 1.0
            for column in range(3):
                rows[3 + r][column] = mechanical[r][column]
                rows[3 + r][6 + column] = converse[r][column]
                rows[6 + r][3 + column] = direct[r][column]
                rows[6 + r][6 + column] = leakage[r][column]
            rows[3 + r][9] = self.b[r] / p.quartz_mass[r]
        rows[6 + c.face_cut][12] = -1.0 / p.capacitance[c.face_cut]
        rows[9][10] = 1.0
        for column in range(3):
            rows[10][column] = self.b[column] / p.acoustic_mass
        rows[10][9] = -p.acoustic_stiffness / p.acoustic_mass
        rows[10][10] = -p.acoustic_damping / p.acoustic_mass
        rows[11][12] = 1.0 / c.storage_capacitance
        rows[12][6 + c.face_cut] = 1.0 / c.carry_inductance
        rows[12][11] = -1.0 / c.carry_inductance
        rows[12][12] = -c.carry_resistance / c.carry_inductance
        return rows

    def step(self, state: CarryState):
        return CarryState.from_vector(nm.matvec(self.transition, state.vector()))

    def energy_parts(self, state: CarryState):
        p, c = self.body, self.carry
        quartz_mechanical = 0.5 * (
            nm.dot(state.velocity, nm.matvec(self.M, state.velocity))
            + nm.dot(state.x, nm.matvec(self.K, state.x)))
        quartz_electrical = 0.5 * nm.dot(state.voltage, nm.matvec(self.C, state.voltage))
        acoustic = 0.5 * (p.acoustic_mass * state.acoustic_velocity ** 2
                          + p.acoustic_stiffness * state.acoustic_displacement ** 2)
        reciprocal_cross = -state.acoustic_displacement * nm.dot(self.b, state.x)
        storage = 0.5 * c.storage_capacitance * state.storage_voltage ** 2
        carry_field = 0.5 * c.carry_inductance * state.carry_current ** 2
        return {"quartz_mechanical": quartz_mechanical,
                "quartz_electrical": quartz_electrical, "acoustic": acoustic,
                "reciprocal_cross": reciprocal_cross, "storage": storage,
                "carry_field": carry_field}

    def energy(self, state: CarryState):
        return sum(self.energy_parts(state).values())

    def loss_power(self, state: CarryState):
        p, c = self.body, self.carry
        return {"electrical": p.electrical_conductance * nm.dot(state.voltage, state.voltage),
                "acoustic": p.acoustic_damping * state.acoustic_velocity ** 2,
                "carry": c.carry_resistance * state.carry_current ** 2}


def initial_carry_state(acoustic_seed: float = 1.0, compression: float = 0.0):
    return CarryState([compression, 0.0, 0.0], [0.0] * 3, [0.0] * 3,
                      acoustic_seed, 0.0, 0.0, 0.0)


def run_carry(body_params: AcousticParameters, carry_params: CarryParameters,
              samples: int = 6000, acoustic_seed: float = 1.0):
    body = CarryBody(body_params, carry_params)
    state = initial_carry_state(acoustic_seed)
    states = [state]
    losses = {"electrical": 0.0, "acoustic": 0.0, "carry": 0.0}
    reversals = []
    previous_current = state.carry_current
    for index in range(1, samples + 1):
        received = body.step(state)
        before_loss, after_loss = body.loss_power(state), body.loss_power(received)
        for name in losses:
            losses[name] += 0.5 * body_params.step * (before_loss[name] + after_loss[name])
        if previous_current != 0.0 and received.carry_current * previous_current <= 0.0:
            reversals.append({"sample_index": index,
                              "observed_time": index * body_params.step,
                              "storage_voltage": received.storage_voltage,
                              "storage_energy": body.energy_parts(received)["storage"]})
        previous_current = received.carry_current
        states.append(received)
        state = received
    initial_energy = body.energy(states[0])
    final_energy = body.energy(states[-1])
    total_loss = sum(losses.values())
    storage_energies = [body.energy_parts(item)["storage"] for item in states]
    return {
        "body_parameters": asdict(body_params), "carry_parameters": asdict(carry_params),
        "timing_status": "current reversals and storage extrema are observed from the coupled state",
        "storage": {"final_voltage": states[-1].storage_voltage,
                    "final_charge": (carry_params.storage_capacitance
                                     * states[-1].storage_voltage),
                    "final_energy": storage_energies[-1],
                    "peak_energy": max(storage_energies),
                    "monotonic": all(b >= a for a, b in zip(storage_energies, storage_energies[1:]))},
        "current_reversals": reversals,
        "energy": {"initial": initial_energy, "final": final_energy,
                   "losses": losses, "closure_residual": final_energy + total_loss - initial_energy},
        "final_parts": body.energy_parts(states[-1]),
        "q_minus_sigma": {"voltage_difference": (states[-1].voltage[carry_params.face_cut]
                                                  - states[-1].storage_voltage),
                          "carry_current": states[-1].carry_current},
    }
