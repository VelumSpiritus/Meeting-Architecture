from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

from acoustic import (AcousticEngine, AcousticParameters, AcousticQuartzBody,
                      initial_acoustic_state, write_acoustic_run)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run quartz + acoustic field + speaker return")
    parser.add_argument("--beats", type=int, default=3000)
    parser.add_argument("--compression", type=float, default=1.0)
    parser.add_argument("--acoustic-seed", type=float, default=0.0)
    parser.add_argument("--speaker-gain", type=float, default=0.0)
    parser.add_argument("--feedback-cut", type=int, choices=(0, 1, 2))
    parser.add_argument("--selection-mode", choices=("residual", "round_robin", "random"),
                        default="residual")
    parser.add_argument("--acoustic-damping", type=float, default=0.01)
    parser.add_argument("--step", type=float, default=0.02)
    args = parser.parse_args()
    if args.beats < 1:
        parser.error("--beats must be positive")
    params = AcousticParameters(speaker_gain=args.speaker_gain,
                                fixed_feedback_cut=args.feedback_cut,
                                selection_mode=args.selection_mode,
                                acoustic_damping=args.acoustic_damping, step=args.step)
    body = AcousticQuartzBody(params)
    engine = AcousticEngine(body)
    states, applications = engine.run(
        initial_acoustic_state(args.compression, args.acoustic_seed), args.beats)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    destination = Path(__file__).resolve().parent / "runs" / f"acoustic-{stamp}"
    write_acoustic_run(destination, params, body, engine, states, applications)
    summary = engine.summary()
    print(f"run: {destination}")
    print(f"triple: {summary['triple']}")
    print(f"source_work: {summary['source_work']:.9g}")
    print(f"dissipated: {summary['dissipated']:.9g}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
