"""Capture-to-F hook: return each product and its next residual address."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "f_operator_engine" / "src"))
from services.ark_coder import f_operator as F


def feed_capture(sigma, entries):
    evidence = json.dumps(entries, sort_keys=True, ensure_ascii=False).encode("utf-8")
    residual = F.project(sigma, evidence)
    F.accrue(sigma, evidence)
    return entries, residual
