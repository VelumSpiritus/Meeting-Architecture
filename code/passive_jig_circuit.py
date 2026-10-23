"""Normalized three-channel passive quartz jig charging one reservoir.

Each pressure event creates three modal open-circuit voltages on finite piezo
capacitances.  Idealized full-wave diode paths conduct only while a source
exceeds reservoir voltage plus threshold.  Charge sharing, diode/path loss,
and reservoir leakage are kept in one energy ledger.

The event's source energy is external mechanical work.  This model tests a
passive charging jig; it does not model a self-powering or infinite reservoir.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from math import exp, sqrt

from topology_tournament import DIAGONAL, SEEDS, dot


MODAL_PORTS = (
    DIAGONAL,
    (1 / sqrt(2), -1 / sqrt(2), 0.0),
    (1 / sqrt(6), 1 / sqrt(6), -2 / sqrt(6)),
)


@dataclass(frozen=True)
class JigCircuitParameters:
    piezo_capacitance: float = 1.0
    reservoir_capacitance: float = 20.0
    diode_drop: float = 0.02
    leakage_conductance: float = 1e-5
    interval: float = 1.0


def _validate(p):
    if p.piezo_capacitance <= 0.0 or p.reservoir_capacitance <= 0.0:
        raise ValueError("capacitances must be positive")
    if p.diode_drop < 0.0 or p.leakage_conductance < 0.0 or p.interval < 0.0:
        raise ValueError("drop, leakage, and interval must be non-negative")


def _capacitor_energy(capacitance, voltage):
    return 0.5 * capacitance * voltage * voltage


def run_jig_circuit(events=1000, parameters=JigCircuitParameters(),
                    seed_order=("center", "dipole", "curvature", "uniform")):
    _validate(parameters)
    if events < 0 or not seed_order:
        raise ValueError("events must be non-negative and seed_order non-empty")
    cp, cr = parameters.piezo_capacitance, parameters.reservoir_capacitance
    reservoir_voltage = 0.0
    mechanical_input = 0.0
    diode_loss = 0.0
    sharing_loss = 0.0
    leakage_loss = 0.0
    transferred_charge = 0.0
    conduction_events = 0
    trace = []

    for index in range(events):
        before_leak = _capacitor_energy(cr, reservoir_voltage)
        reservoir_voltage *= exp(-parameters.leakage_conductance
                                 * parameters.interval / cr)
        after_leak = _capacitor_energy(cr, reservoir_voltage)
        leakage_loss += before_leak - after_leak

        name = seed_order[index % len(seed_order)]
        sign = 1.0 if index % 2 == 0 else -1.0
        source_voltages = [sign * dot(port, SEEDS[name]) for port in MODAL_PORTS]
        source_energy = sum(_capacitor_energy(cp, voltage)
                            for voltage in source_voltages)
        mechanical_input += source_energy
        event_diode = event_sharing = event_charge = 0.0

        # The bridges are simultaneous in hardware.  Iterating the greatest
        # overdrive first is the zero-resistance equilibrium construction; a
        # port can conduct once per pressure event as its finite Cp discharges.
        remaining = list(enumerate(abs(value) for value in source_voltages))
        while remaining:
            channel, source_voltage = max(
                remaining, key=lambda item: item[1] - reservoir_voltage)
            remaining = [item for item in remaining if item[0] != channel]
            overdrive = source_voltage - reservoir_voltage - parameters.diode_drop
            if overdrive <= 0.0:
                continue
            charge = cp * cr / (cp + cr) * overdrive
            old_source = source_voltage
            old_reservoir = reservoir_voltage
            source_voltage -= charge / cp
            reservoir_voltage += charge / cr
            before = (_capacitor_energy(cp, old_source)
                      + _capacitor_energy(cr, old_reservoir))
            after = (_capacitor_energy(cp, source_voltage)
                     + _capacitor_energy(cr, reservoir_voltage))
            drop_loss = parameters.diode_drop * charge
            path_loss = max(0.0, before - after - drop_loss)
            diode_loss += drop_loss
            sharing_loss += path_loss
            event_diode += drop_loss
            event_sharing += path_loss
            event_charge += charge
            transferred_charge += charge
            conduction_events += 1

        # Source capacitances relax mechanically after the event.  Whatever
        # source energy was not carried is returned/damped at the jig boundary.
        reservoir_gain = (_capacitor_energy(cr, reservoir_voltage)
                          - after_leak)
        uncaptured = max(0.0, source_energy - reservoir_gain
                         - event_diode - event_sharing)
        sharing_loss += uncaptured
        event_sharing += uncaptured
        if index < 8 or index == events - 1:
            trace.append({"event": index + 1, "seed": name, "polarity": sign,
                          "source_voltages": source_voltages,
                          "charge_carried": event_charge,
                          "reservoir_voltage": reservoir_voltage,
                          "reservoir_energy": _capacitor_energy(cr, reservoir_voltage)})

    held = _capacitor_energy(cr, reservoir_voltage)
    closure = held + diode_loss + sharing_loss + leakage_loss - mechanical_input
    return {
        "parameters": asdict(parameters),
        "events": events,
        "seed_order": list(seed_order),
        "conduction_events": conduction_events,
        "trace": trace,
        "reservoir": {"voltage": reservoir_voltage, "energy": held,
                      "capacity": cr},
        "energy": {"mechanical_input": mechanical_input,
                   "held": held, "diode_loss": diode_loss,
                   "charge_sharing_and_return_loss": sharing_loss,
                   "leakage_loss": leakage_loss,
                   "closure_residual": closure},
        "charge_carried": transferred_charge,
        "q_minus_sigma": (
            "The reservoir voltage eventually blocks weaker modal ports; leakage, path loss, "
            "and uncarried source energy remain physical residual rather than recurring charge."
        ),
    }
