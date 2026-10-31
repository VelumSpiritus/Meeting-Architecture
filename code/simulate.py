from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

from engine import QuartzEngine, QuartzBody, QuartzParameters, initial_compression, write_run


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the passive three-mode quartz engine")
    parser.add_argument("--beats", type=int, default=600)
    parser.add_argument("--compression", type=float, default=1.0)
    parser.add_argument("--axis", type=int, choices=(0, 1, 2), default=0)
    parser.add_argument("--return-conductance", type=float, default=0.0)
    parser.add_argument("--step", type=float, default=0.04)
    args = parser.parse_args()

    if args.beats < 1:
        parser.error("--beats must be positive")
    params = QuartzParameters(return_conductance=args.return_conductance, step=args.step)
    body = QuartzBody(params)
    engine = QuartzEngine(body)
    states, applications = engine.run(initial_compression(args.compression, args.axis), args.beats)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    destination = Path(__file__).resolve().parent / "runs" / stamp
    write_run(destination, params, body, engine, states, applications)
    summary = engine.summary()
    print(f"run: {destination}")
    print(f"triple: {summary['triple']}")
    print(f"rho12_all: {summary['rho12_all']}")
    print(f"rho3_refuters: {len(summary['rho3'])}")
    return 1 if summary["rho3"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
