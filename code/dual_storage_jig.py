"""Dual-output jig: 10 uF measurement buffer or harvested battery carry.

The quartz front end is represented by measured-at-the-bus energy per acoustic
event.  That parameter is swept because the raw stone has not yet been
electrically characterized.  The battery branch models BQ25570-like cold start,
continuous-harvest floor, conversion efficiency, and operating current.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from math import sqrt


@dataclass(frozen=True)
class DualJigParameters:
    buffer_capacitance: float = 10e-6
    cold_start_voltage: float = 0.6
    harvest_floor_voltage: float = 0.1
    harvester_efficiency: float = 0.90
    harvester_operating_current: float = 488e-9
    input_clamp_voltage: float = 5.1
    event_frequency: float = 10.0
    duration: float = 3600.0
    battery_nominal_voltage: float = 3.2
    battery_capacity_ah: float = 0.05
    initial_battery_soc: float = 0.50


def _validate(p):
    positive = (p.buffer_capacitance, p.cold_start_voltage,
                p.harvest_floor_voltage, p.input_clamp_voltage,
                p.event_frequency, p.duration,
                p.battery_nominal_voltage, p.battery_capacity_ah)
    if any(value <= 0.0 for value in positive):
        raise ValueError("capacitance, voltages, time, frequency, and capacity must be positive")
    if not 0.0 <= p.harvester_efficiency <= 1.0:
        raise ValueError("harvester_efficiency must lie in [0, 1]")
    if not 0.0 <= p.initial_battery_soc <= 1.0 or p.harvester_operating_current < 0.0:
        raise ValueError("SOC must lie in [0, 1] and current be non-negative")


def run_measure_branch(event_energy, parameters=DualJigParameters()):
    _validate(parameters)
    if event_energy < 0.0:
        raise ValueError("event_energy must be non-negative")
    events = int(parameters.event_frequency * parameters.duration)
    held = events * event_energy
    voltage = sqrt(2.0 * held / parameters.buffer_capacitance) if held else 0.0
    return {"events": events, "event_energy": event_energy,
            "buffer_energy": held, "buffer_voltage": voltage,
            "closure_residual": held - events * event_energy}


def run_battery_branch(event_energy, parameters=DualJigParameters()):
    _validate(parameters)
    if event_energy < 0.0:
        raise ValueError("event_energy must be non-negative")
    p = parameters
    events = int(p.event_frequency * p.duration)
    dt = 1.0 / p.event_frequency
    buffer_energy = battery_gain = conversion_loss = operating_loss = 0.0
    input_energy = events * event_energy
    clamp_loss = 0.0
    active = False
    cold_start_event = None
    transfer_events = 0
    cold_energy = 0.5 * p.buffer_capacitance * p.cold_start_voltage ** 2
    floor_energy = 0.5 * p.buffer_capacitance * p.harvest_floor_voltage ** 2
    trace = []

    for index in range(1, events + 1):
        buffer_energy += event_energy
        clamp_energy = 0.5 * p.buffer_capacitance * p.input_clamp_voltage ** 2
        if buffer_energy > clamp_energy:
            clamp_loss += buffer_energy - clamp_energy
            buffer_energy = clamp_energy
        if not active and buffer_energy >= cold_energy:
            active = True
            cold_start_event = index
        if active:
            voltage = sqrt(2.0 * buffer_energy / p.buffer_capacitance)
            idle = min(buffer_energy, voltage * p.harvester_operating_current * dt)
            buffer_energy -= idle
            operating_loss += idle
            transferable = max(0.0, buffer_energy - floor_energy)
            if transferable > 0.0:
                held = p.harvester_efficiency * transferable
                battery_gain += held
                conversion_loss += transferable - held
                buffer_energy -= transferable
                transfer_events += 1
        if index <= 5 or index in (events // 2, events):
            trace.append({"event": index, "active": active,
                          "buffer_voltage": sqrt(2.0 * buffer_energy / p.buffer_capacitance)
                          if buffer_energy else 0.0,
                          "battery_gain": battery_gain})

    battery_capacity = p.battery_nominal_voltage * p.battery_capacity_ah * 3600.0
    soc_gain = battery_gain / battery_capacity
    final_soc = min(1.0, p.initial_battery_soc + soc_gain)
    # This low-energy model does not enter CV taper. Energy exceeding the
    # declared cell capacity is retained as a named protection residual.
    accepted_gain = max(0.0, final_soc - p.initial_battery_soc) * battery_capacity
    protection_residual = battery_gain - accepted_gain
    closure = (buffer_energy + accepted_gain + protection_residual + conversion_loss
               + operating_loss + clamp_loss - input_energy)
    return {
        "parameters": asdict(p), "events": events, "event_energy": event_energy,
        "cold_started": active, "cold_start_event": cold_start_event,
        "cold_start_time": cold_start_event * dt if cold_start_event else None,
        "transfer_events": transfer_events, "trace": trace,
        "buffer": {"energy": buffer_energy,
                   "voltage": sqrt(2.0 * buffer_energy / p.buffer_capacitance)
                   if buffer_energy else 0.0},
        "battery": {"accepted_energy": accepted_gain, "soc_gain": soc_gain,
                    "final_soc": final_soc,
                    "capacity_energy": battery_capacity},
        "energy": {"input": input_energy, "conversion_loss": conversion_loss,
                   "harvester_operating_loss": operating_loss,
                   "input_clamp_loss": clamp_loss,
                   "battery_protection_residual": protection_residual,
                   "closure_residual": closure},
        "q_minus_sigma": (
            "Event energy is the unmeasured physical variable. Battery CV taper, temperature, "
            "cell-specific limits, and board resistor configuration are not instantiated."
        ),
    }
