"""Portable entry point for the unmodified Vigil F_operator core."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from services.ark_coder import f_operator as F  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Read bytes through the F_operator")
    parser.add_argument("input", nargs="?", type=Path, help="file to read; a built-in byte sample is used if omitted")
    args = parser.parse_args()

    data = args.input.read_bytes() if args.input else b"A B A B A B\n"
    sigma = F.new_sigma()
    before = F.project(sigma, data)
    F.accrue(sigma, data)
    after = F.project(sigma, data)
    print(json.dumps({
        "source": str(args.input) if args.input else "built-in byte sample",
        "input_hex": data.hex(),
        "residual_bits_per_byte_before_accrual": before,
        "residual_bits_per_byte_after_accrual": after,
        "application": "received bytes projected and accrued",
    }, indent=2))


if __name__ == "__main__":
    main()
