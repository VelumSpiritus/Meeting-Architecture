"""End-to-end battery-form simulation and functional Occam ablation.

The model starts with an explicitly supplied 100 N mechanical event measured
through the existing 28 g quartz surrogate and ends at energy accepted by a
protected lithium-ion pack.  It computes event counts algebraically; no clock
drives the recurrence.  Observer time is reported only when a rate is supplied.

This is a design model, not authorization to connect a raw pack.  Pack series
count, chemistry, maximum voltage, temperature limits, and BMS/charger
compatibility must be verified from the actual battery label and service data.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from math import ceil, pi

from measured_crystal_surrogate import PE_EMIS_FREE, SurrogateRun, measured_event
from quartz_tensor_orientation import rotation_z_y_z


@dataclass(frozen=True)
class BatteryFormParameters:
    force_n: float = 100.0
    euler_degrees: tuple[float, float, float] = (0.0, 90.0, 0.0)
    resonant_strain_capture: float = 0.75
    electrode_collection_efficiency: float = 0.95
    polarity_capture_efficiency: float = 0.85
    converter_efficiency: float = 0.80
    buffer_capacitance_f: float = 10e-6
    charger_cold_start_voltage_v: float = 1.0
    pack_marketing_voltage_v: float = 40.0
    pack_charge_voltage_v: float = 42.0
    pack_capacity_ah: float = 6.0
    initial_soc: float = 0.20
    target_soc: float = 1.0
    observer_event_rate_hz: float | None = None


@dataclass(frozen=True)
class JigForm:
    supplied_actuation: bool = True
    resonant_clamp: bool = True
    electrode_pair: bool = True
    polarity_capture: bool = True
    buffer: bool = True
    cc_cv_converter: bool = True
    pack_protection: bool = True


def _validate(p: BatteryFormParameters):
    if p.force_n < 0 or p.buffer_capacitance_f <= 0:
        raise ValueError("force must be nonnegative and buffer capacitance positive")
    for name in ("resonant_strain_capture", "electrode_collection_efficiency",
                 "polarity_capture_efficiency", "converter_efficiency",
                 "initial_soc", "target_soc"):
        value = getattr(p, name)
        if not 0.0 <= value <= 1.0:
            raise ValueError(f"{name} must lie in [0,1]")
    if p.target_soc < p.initial_soc:
        raise ValueError("target SOC cannot be below initial SOC")
    if min(p.pack_marketing_voltage_v, p.pack_charge_voltage_v,
           p.pack_capacity_ah, p.charger_cold_start_voltage_v) <= 0:
        raise ValueError("pack and charger values must be positive")
    if p.observer_event_rate_hz is not None and p.observer_event_rate_hz <= 0:
        raise ValueError("observer event rate must be positive when supplied")


def _missing_organs(jig: JigForm):
    names = {
        "supplied_actuation": "no fresh mechanical/acoustic energy enters",
        "resonant_clamp": "source does not form controlled strain in the quartz",
        "electrode_pair": "piezoelectric charge has no collection boundary",
        "polarity_capture": "alternating charge is not folded toward one DC ground",
        "buffer": "intermittent charge cannot accumulate to converter cold start",
        "cc_cv_converter": "buffer has no regulated CC/CV path into pack chemistry",
        "pack_protection": "cell-level voltage/temperature/protection boundary is absent",
    }
    return [message for field, message in names.items() if not getattr(jig, field)]


def run_battery_form(p=BatteryFormParameters(), jig=JigForm()):
    _validate(p)
    missing = _missing_organs(jig)
    angles = tuple(value*pi/180.0 for value in p.euler_degrees)
    event = measured_event(p.force_n, rotation_z_y_z(*angles), PE_EMIS_FREE,
                           SurrogateRun(force=p.force_n))
    mechanical = event["mechanical_energy_joule"] if jig.supplied_actuation else 0.0
    piezo = event["open_circuit_electrical_joule"] if all((
        jig.supplied_actuation, jig.resonant_clamp, jig.electrode_pair)) else 0.0
    after_clamp = piezo*p.resonant_strain_capture if jig.resonant_clamp else 0.0
    collected = (after_clamp*p.electrode_collection_efficiency
                 if jig.electrode_pair else 0.0)
    dc = collected*p.polarity_capture_efficiency if jig.polarity_capture else 0.0
    accepted = dc*p.converter_efficiency if all((jig.buffer,
                                                  jig.cc_cv_converter,
                                                  jig.pack_protection)) else 0.0

    buffer_cold_j = 0.5*p.buffer_capacitance_f*p.charger_cold_start_voltage_v**2
    events_to_cold = ceil(buffer_cold_j/dc) if dc > 0 else None
    # Marketing voltage is used for label-basis energy only; charge voltage is
    # retained separately and must be verified against the actual series stack.
    pack_label_capacity_j = p.pack_marketing_voltage_v*p.pack_capacity_ah*3600.0
    target_delta_j = (p.target_soc-p.initial_soc)*pack_label_capacity_j
    events_to_target = ceil(target_delta_j/accepted) if accepted > 0 else None
    observer_seconds = (events_to_target/p.observer_event_rate_hz
                        if events_to_target is not None and
                        p.observer_event_rate_hz is not None else None)

    clamp_residual = max(0.0, piezo-after_clamp)
    electrode_residual = max(0.0, after_clamp-collected)
    polarity_residual = max(0.0, collected-dc)
    conversion_residual = max(0.0, dc-accepted)
    unconverted_mechanical = max(0.0, mechanical-piezo)
    closure = (accepted+conversion_residual+polarity_residual+
               electrode_residual+clamp_residual+unconverted_mechanical-mechanical)
    formed = not missing and accepted > 0
    return {
        "status": "battery-form-path-closed" if formed else "open",
        "parameters": asdict(p),
        "jig": asdict(jig),
        "material_event": event,
        "per_application": {
            "supplied_mechanical_joule": mechanical,
            "quartz_open_circuit_joule": piezo,
            "buffer_dc_joule": dc,
            "accepted_by_pack_joule": accepted,
        },
        "formation": {
            "buffer_cold_start_joule": buffer_cold_j,
            "applications_to_cold_start": events_to_cold,
            "pack_label_capacity_joule": pack_label_capacity_j,
            "target_stored_delta_joule": target_delta_j,
            "applications_to_target_soc": events_to_target,
            "observer_seconds_at_supplied_rate": observer_seconds,
        },
        "ledger": {
            "unconverted_mechanical_joule": unconverted_mechanical,
            "clamp_residual_joule": clamp_residual,
            "electrode_residual_joule": electrode_residual,
            "polarity_residual_joule": polarity_residual,
            "conversion_residual_joule": conversion_residual,
            "closure_residual_joule": closure,
        },
        "triple": {
            "P_being": "energy accepted under the pack's protected CC/CV boundary",
            "q_minus_sigma_emergence": missing or [
                "actual pack series count, chemistry, cell voltages and temperature limits",
                "measured resonant clamp transfer and Q",
                "measured electrode/contact and harvester cold-start curves",
            ],
            "Lambda_plus": "every supplied, carried, accepted and residual joule retained",
        },
        "rho3": {
            "ledger_closed": abs(closure) <= max(1e-24, 1e-10*mechanical),
            "refuter": "pack energy cannot exceed explicitly supplied mechanical energy",
            "pack_voltage_warning": (
                "40 V is treated as a marketing/label value; 42 V charge voltage is a "
                "configurable hypothesis, not permission to charge the unidentified pack"
            ),
        },
    }


def occam_ablation(p=BatteryFormParameters()):
    full = JigForm()
    fields = tuple(asdict(full))
    rows = {"full": run_battery_form(p, full)}
    for field in fields:
        rows["without_"+field] = run_battery_form(p, replace(full, **{field: False}))
    indispensable = [field for field in fields
                     if rows["without_"+field]["status"] != "battery-form-path-closed"]
    external_jig_organs = [x for x in indispensable
                           if x not in ("supplied_actuation", "pack_protection")]
    return {
        "indispensable_functions": indispensable,
        "minimum_external_jig_organs_if_pack_protection_is_verified": external_jig_organs,
        "rows": rows,
    }

