"""Read system-derived return events and the complete physical energy ledger."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from acoustic import ARKAcoustic, AcousticParameters, AcousticQuartzBody, initial_acoustic_state


@dataclass(frozen=True)
class ReturnEvent:
    index: int
    time: float
    voltage_norm: float
    stored_energy: float


def voltage_norm(state) -> float:
    return sum(value * value for value in state.voltage) ** 0.5


def return_events(states, body: AcousticQuartzBody) -> list[ReturnEvent]:
    """Local voltage-norm maxima; their times are read, never scheduled."""
    magnitudes = [voltage_norm(state) for state in states]
    events: list[ReturnEvent] = []
    for index in range(1, len(states) - 1):
        if magnitudes[index] > magnitudes[index - 1] and magnitudes[index] >= magnitudes[index + 1]:
            events.append(ReturnEvent(index, index * body.params.step, magnitudes[index],
                                      body.stored_energy(states[index])))
    return events


def run_recurrence(params: AcousticParameters, samples: int = 6000,
                   compression: float = 1.0, acoustic_seed: float = 0.0) -> dict[str, Any]:
    body = AcousticQuartzBody(params)
    engine = ARKAcoustic(body)
    states, _ = engine.run(initial_acoustic_state(compression, acoustic_seed), samples)
    events = return_events(states, body)
    summary = engine.summary()
    initial = body.stored_energy(states[0])
    final = body.stored_energy(states[-1])
    accounted_final = (final + summary["internal_electrical_loss"]
                        + summary["acoustic_loss"] + summary["delivered_load_work"])
    closure_residual = accounted_final - initial - summary["source_work"]
    intervals = [b.time - a.time for a, b in zip(events, events[1:])]
    return {
        "parameters": asdict(params),
        "samples": samples,
        "seed": {"quartz_compression": compression, "acoustic_displacement": acoustic_seed},
        "observer_step": params.step,
        "timing_status": "return times derived from state extrema; observer step is not a drive clock",
        "event_count": len(events),
        "events": [asdict(event) for event in events],
        "return_intervals": intervals,
        "first_return_time": events[0].time if events else None,
        "last_return_time": events[-1].time if events else None,
        "peak_return_voltage": max((event.voltage_norm for event in events), default=0.0),
        "return_decay_ratio": (events[-1].voltage_norm / events[0].voltage_norm
                               if len(events) > 1 and events[0].voltage_norm else None),
        "energy": {
            "initial_seed": initial,
            "final_stored": final,
            "active_source_work": summary["source_work"],
            "internal_electrical_loss": summary["internal_electrical_loss"],
            "acoustic_loss": summary["acoustic_loss"],
            "delivered_load_work": summary["delivered_load_work"],
            "closure_residual": closure_residual,
        },
        "triple": summary["triple"],
    }
