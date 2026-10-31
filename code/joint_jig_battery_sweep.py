"""Joint acoustic/electrode jig through a 10 uF buffer into battery storage.

The source is acoustic power. Every downstream gain is therefore bounded by
that supplied power. High-frequency cycles are power-integrated; no invented
per-event energy or clocked electrode selector is used.
"""
from dataclasses import dataclass, asdict
from math import sqrt


@dataclass(frozen=True)
class PhysicalChain:
    acoustic_power_w: float
    contact_efficiency: float
    modal_capture: float
    piezo_efficiency: float
    rectifier_efficiency: float = .88
    harvester_efficiency: float = .90
    buffer_capacitance_f: float = 10e-6
    cold_start_voltage_v: float = .6
    buffer_floor_voltage_v: float = .1
    clamp_voltage_v: float = 5.1
    harvester_quiescent_w: float = 1.6e-6
    duration_s: float = 3600.0
    battery_voltage_v: float = 3.7
    battery_capacity_ah: float = 5.0  # two typical 2.5 Ah 18650 cells in parallel
    initial_soc: float = .50


def _check(p):
    if min(p.acoustic_power_w, p.buffer_capacitance_f, p.duration_s,
           p.battery_voltage_v, p.battery_capacity_ah) <= 0:
        raise ValueError("power, capacitance, duration and battery values must be positive")
    for x in (p.contact_efficiency, p.modal_capture, p.piezo_efficiency,
              p.rectifier_efficiency, p.harvester_efficiency, p.initial_soc):
        if not 0 <= x <= 1: raise ValueError("fractions must lie in [0,1]")


def run_chain(p):
    _check(p)
    acoustic_in = p.acoustic_power_w*p.duration_s
    after_contact = acoustic_in*p.contact_efficiency
    after_modal = after_contact*p.modal_capture
    piezo_electric = after_modal*p.piezo_efficiency
    rectified = piezo_electric*p.rectifier_efficiency
    contact_loss = acoustic_in-after_contact
    modal_loss = after_contact-after_modal
    piezo_loss = after_modal-piezo_electric
    rectifier_loss = piezo_electric-rectified

    cold_e = .5*p.buffer_capacitance_f*p.cold_start_voltage_v**2
    floor_e = .5*p.buffer_capacitance_f*p.buffer_floor_voltage_v**2
    clamp_e = .5*p.buffer_capacitance_f*p.clamp_voltage_v**2
    rectified_power = rectified/p.duration_s
    cold_started = rectified >= cold_e
    cold_start_s = cold_e/rectified_power if cold_started else None

    held_buffer = min(rectified, cold_e if not cold_started else floor_e)
    transfer_input = max(0.0, rectified-held_buffer)
    active_s = max(0.0, p.duration_s-(cold_start_s or p.duration_s))
    operating_loss = min(transfer_input, p.harvester_quiescent_w*active_s)
    transfer_input -= operating_loss
    battery_raw = transfer_input*p.harvester_efficiency
    conversion_loss = transfer_input-battery_raw

    capacity_j = p.battery_voltage_v*p.battery_capacity_ah*3600
    room_j = (1-p.initial_soc)*capacity_j
    accepted = min(room_j, battery_raw)
    protection_residual = battery_raw-accepted
    final_soc = p.initial_soc + accepted/capacity_j
    buffer_v = sqrt(2*held_buffer/p.buffer_capacitance_f) if held_buffer else 0.0
    clamp_loss = 0.0
    if buffer_v > p.clamp_voltage_v:
        clamp_loss = held_buffer-clamp_e; held_buffer=clamp_e; buffer_v=p.clamp_voltage_v

    closure = (contact_loss+modal_loss+piezo_loss+rectifier_loss+held_buffer+
               operating_loss+conversion_loss+accepted+protection_residual+
               clamp_loss-acoustic_in)
    return {"parameters": asdict(p), "cold_started": cold_started,
            "cold_start_s": cold_start_s,
            "power": {"acoustic_w": p.acoustic_power_w,
                      "rectified_electrical_w": rectified_power,
                      "battery_average_w": accepted/p.duration_s},
            "buffer": {"voltage_v": buffer_v, "energy_j": held_buffer},
            "battery": {"accepted_j": accepted, "mah_added": accepted/p.battery_voltage_v/3.6,
                        "soc_gain": accepted/capacity_j, "final_soc": final_soc},
            "loss_j": {"contact": contact_loss, "uncaptured_modes": modal_loss,
                       "piezo_mechanical": piezo_loss, "rectifier": rectifier_loss,
                       "harvester_operating": operating_loss, "conversion": conversion_loss,
                       "protection_residual": protection_residual, "clamp": clamp_loss},
            "closure_residual_j": closure}


def sweep():
    rows=[]
    # 3x3 + two-source relation: four modes robustly visible of eight modeled.
    modal_capture=.5
    for power in (1e-3, 1e-2, .1, 1.0, 10.0):
        for contact in (.01, .10, .50):
            for piezo in (.001, .01, .10):
                rows.append(run_chain(PhysicalChain(power, contact, modal_capture, piezo)))
    return {"model":"3x3 segmented electrodes + two relational acoustic components",
            "assumption":"modal capture 4/8; contact and raw-stone piezo efficiency swept",
            "rows":rows,
            "triple":{"P":"bounded acoustic input carried into buffer and battery",
                      "residual":"measured contact coupling, stone impedance, electrode capacitance, and actual open-circuit voltage",
                      "accrual":"closed energy ledgers over 45 physical scenarios"}}
