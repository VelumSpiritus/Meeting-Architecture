"""Discrete full-pack simulation: harvest, accumulate, then run an OEM charger.

Every minute is executed. Resonance improves captured fraction but never creates
power: captured acoustic power remains <= the independently driven array input.
"""
from dataclasses import dataclass, asdict
from itertools import product


@dataclass(frozen=True)
class FullPack:
    acoustic_w_per_crystal: float = 10.0
    crystals: int = 1
    contact_fraction: float = .1
    resonance_capture_gain: float = 1.0
    modal_fraction: float = .5
    piezo_fraction: float = .01
    rectifier_fraction: float = .88
    harvester_fraction: float = .90
    accumulator_wh: float = 300.0
    inverter_fraction: float = .90
    charger_input_w: float = 250.0
    charger_fraction: float = .86
    pack_wh: float = 216.0
    maximum_days: float = 730.0
    step_seconds: float = 60.0


def run_full_pack(p=FullPack()):
    effective_contact=min(1.0,p.contact_fraction*p.resonance_capture_gain)
    acoustic_w=p.acoustic_w_per_crystal*p.crystals
    harvested_w=(acoustic_w*effective_contact*p.modal_fraction*p.piezo_fraction*
                 p.rectifier_fraction*p.harvester_fraction)
    accumulator_j=pack_j=spill_j=inverter_loss=charger_loss=0.0
    acoustic_j=0.0
    accumulator_cap_j=p.accumulator_wh*3600
    target_j=p.pack_wh*3600
    charger_minute_j=p.charger_input_w*p.step_seconds
    max_steps=int(p.maximum_days*86400/p.step_seconds)
    bursts=0; trace=[]
    for step in range(1,max_steps+1):
        event_acoustic=acoustic_w*p.step_seconds
        acoustic_j+=event_acoustic
        accumulator_j+=harvested_w*p.step_seconds
        if accumulator_j>accumulator_cap_j:
            spill_j+=accumulator_j-accumulator_cap_j; accumulator_j=accumulator_cap_j
        # A real OEM charger is either supplied at its operating input or off.
        if accumulator_j>=charger_minute_j and pack_j<target_j:
            accumulator_j-=charger_minute_j
            after_inverter=charger_minute_j*p.inverter_fraction
            inverter_loss+=charger_minute_j-after_inverter
            accepted=min(target_j-pack_j,after_inverter*p.charger_fraction)
            charger_loss+=after_inverter-accepted
            pack_j+=accepted; bursts+=1
        if step in (1,10,1000,100000) or pack_j>=target_j or step==max_steps:
            trace.append({"minute":step,"day":step*p.step_seconds/86400,
                          "accumulator_wh":accumulator_j/3600,
                          "pack_wh":pack_j/3600,"charger_minutes":bursts})
        if pack_j>=target_j: break
    chain_loss=acoustic_j-(harvested_w*p.step_seconds*step)
    harvested_total=harvested_w*p.step_seconds*step
    # Energy held + post-harvester losses closes against acoustic input.
    closure=(chain_loss+spill_j+accumulator_j+inverter_loss+charger_loss+pack_j-acoustic_j)
    return {"parameters":asdict(p),"completed":pack_j>=target_j,
            "elapsed_days":step*p.step_seconds/86400,"steps_executed":step,
            "charger_bursts":bursts,"power":{"acoustic_w":acoustic_w,
            "harvested_w":harvested_w},"energy":{"acoustic_wh":acoustic_j/3600,
            "harvested_wh":harvested_total/3600,"pack_wh":pack_j/3600,
            "accumulator_wh":accumulator_j/3600,"spill_wh":spill_j/3600,
            "closure_j":closure},"trace":trace}


def sweep_full_pack():
    rows=[]
    for crystals,contact,piezo,resonance in product((1,4,16,64),(.1,.5),(.01,.1),(1,5)):
        rows.append(run_full_pack(FullPack(crystals=crystals,contact_fraction=contact,
                                          piezo_fraction=piezo,
                                          resonance_capture_gain=resonance)))
    completed=[r for r in rows if r["completed"]]
    completed.sort(key=lambda r:r["elapsed_days"])
    return {"model":"minute-stepped quartz array -> accumulator -> 250 W OEM charger -> 216 Wh pack",
            "scenarios":len(rows),"completed":len(completed),"fastest":completed[:10],
            "rows":rows,"triple":{"P":"full-size configurations that actually reach 216 Wh",
            "q_minus_sigma":"brand-specific charger startup, measured stone coupling and resonance",
            "Lambda_plus":"every accumulator and charger minute executed with a closed ledger"}}
