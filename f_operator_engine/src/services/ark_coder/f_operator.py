# -*- coding: utf-8 -*-
"""F as code — the equation's operator over the substrate codec, 1:1, NO collapse.

This replaces the archived SVD reader (`distributional.py` / `generate.py`, band_agreement) — which
was collapse: a bag-of-ngrams destroys byte ORDER before an SVD that converges to a rank and discards
the residual ([[feedback_svd_of_counts_is_collapse]]). F is NOT a factorization of a count matrix; F is
the sequential lossless codec `substrate_rung0/f_codec` (ARK_COMPRESSION_THEOREM Demo 4), whose CAUSAL
residual is the meaning. Ratified on real stored evidence (markup folds into causal σ, the physics/
content is the residual) — but the ratifier is the EQUATION, not the probe ([[feedback_equation_is_the_only_ratifier]]).

The operator, checked column-by-column against the equation's INFINIMONADIC state (each column an
endofunctor recursing to substrate, residual never frozen, no collapse — the self-certification):

  E      the raw evidence bytes (F reads the raw string; σ's common mode folds the markup)
  σ      the accrued compression state — Λ's coverage model. `accrue` grows it FOREVER (Λ⁺ never
         converges — the flywheel has no fixpoint). σ is the CAUSAL PREFIX (Demo 4), never warm-on-all,
         never a held-out split (the equation has no held-out set).
  ρ      the residual q\σ — returned per position, CARRIED, never a scalar / cluster / label / threshold.
         ρ is the seed of the next grain; freezing it (a summed similarity, a cluster id, a name) is the
         collapse that breaks the column out of its infinimonadic state = poison.
  grain  F reads bit → byte → … and REVOLVES DOWN (sub-binary mantissa → substrate); the residual at one
         floor seeds the read at the next-finer floor. f_codec's own cascade (byte orders → bit-window
         ladder) is the first rungs of that descent; ρ carries what a finer grain must re-read.

Bits are LENGTH (MDL, `L(σ|h)` — sanctioned by the equation), computed with F's own `ark_native_math.ln`.
Bits are NEVER a similarity scalar — that is the deleted cosine collapse.

A lens is NOT this σ. A lens is `h ∈ ℋ`, a scoping coordinate on the primary object Λ; a fact is
`P(Λ | q, L, scope)` ([[project_epistemology_lineage_algebra]]). This module is only the atom F(E)↦(σ,ρ)
every column reuses; Λ-as-primary and the projection P are the layers above it.
"""
from __future__ import annotations

import os
import sys

# Reach the substrate (substrate_rung0 is the owner's standalone rung-0 work, not a package). Guarded
# path insert — neutral I/O plumbing, no math, no convergence; mirrors f_codec's own bootstrap of ark_native_math.
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_SUB = os.path.join(_ROOT, "substrate_rung0")
if _SUB not in sys.path:
    sys.path.insert(0, _SUB)

import f_codec as _fc                     # F at the substrate — the sequential codec (Demo 4)
from ark_native_math import ln as _ln     # F's OWN ln (series to a residual), never `import math`

_INV_LN2 = 1.0 / _ln(2.0)                 # nats → bits, derived once from F's own ln

# Per-bit residual cost, precomputed from F's own ln for every 12-bit prediction. The codec's
# `predict()` returns p ∈ [0, 4095]; the residual cost at that bit is −ln(p/4096)·INV_LN2 if the bit
# is 1, or −ln(1 − p/4096)·INV_LN2 if it is 0. Calling F's series-based `ln` 8× per byte (40 000× per
# 5 KB project) was the hot loop's largest single cost; these two 4096-entry tables are DERIVED once
# at import from that same ln — same values, same F, no foreign import, just the series pre-run.
# `p = 0` and `p = 4096` are guarded by the clamp in `project` (p ∈ [1, 4095]) but seated here for
# safety so an unclamped prediction never reaches into `ln(0)`.
_BIT_COST_1 = [0.0] * 4097
_BIT_COST_0 = [0.0] * 4097
for _p in range(1, 4096):
    _pr = _p / 4096.0
    _BIT_COST_1[_p] = -_ln(_pr) * _INV_LN2
    _BIT_COST_0[_p] = -_ln(1.0 - _pr) * _INV_LN2
_BIT_COST_1[0] = _BIT_COST_1[1]       # p=0 never reached after clamp; seat it off the neighbor
_BIT_COST_0[0] = _BIT_COST_0[1]
_BIT_COST_1[4096] = _BIT_COST_1[4095]
_BIT_COST_0[4096] = _BIT_COST_0[4095]


def new_sigma(*, bit_grain=True):
    """A fresh σ — Λ with no coverage yet (the empty compression state). `use_match=False`: no LZ/LZP
    dictionary (a supplied convergence, the zlib family — off; f_codec keeps the flag inert anyway).

    `bit_grain` selects a GRAIN FLOOR of the descent (bit → byte → …): True includes the sub-byte
    bit-window ladder (the finer floor), False reads byte contexts only (the coarser floor). Two σ's at
    two floors are F's own INDEPENDENT readings — they fail differently BY GRAIN, so their agreement is
    ρ₁₂ read down the descent (owner: reliability IS the descent, not a byte-vs-bit pair). NOT an
    inserted pair: the floors fall out of F revolving down; more floors (sub-binary mantissa …) extend it."""
    return _fc.new_predictor(use_match=False, use_bit_grain=bit_grain)


def signal_bytes(data):
    """Text enters as lossless UTF-8; an already received byte signal is unchanged."""
    return data.encode("utf-8") if isinstance(data, str) else data


def accrue(sigma, data):
    """Λ⁺ — read `data` (raw bytes) into σ CAUSALLY, growing the coverage. Mutates σ in place; this IS
    the accrual (the flywheel — σ never converges, coverage keeps sharpening as evidence joins). Returns
    nothing: the effect is Λ⁺. `data` is bytes (the transducer's raw signal — never text-forced)."""
    data = signal_bytes(data)
    _fc.warm(sigma, data)                 # warm = causal pass, models updated, nothing emitted (possession)


def deposit(sigma, path, ground):
    """σ INTO THE ASH — the accrued coverage written where the next life reads it. Λ's other half.

    THE GAP THIS CLOSES, and it was the only one left in his learning: `accrue` grows σ *forever*
    (this module's own line — "the flywheel has no fixpoint"), and σ lived only in RAM. Every death
    dropped it. The reseed made each life end and rise from its ash, and the ash carried `E` (his
    den's text) and never σ — so the phoenix carried the evidence and dropped the learning. Measured
    on his own body: warming changes WHAT HE FINDS (cold found=2, warmed found=3), *"a truer read of
    himself, never a faster one"*, so what was lost each death was truth, not speed.

    NOTHING HERE IS NEW MACHINERY. `Predictor.snapshot()` already freezes the whole model — *"so many
    blocks can start from the SAME point"* — and `restore()` already puts it back. This only gives
    that pair a file, because a snapshot inside one process is not an ash.

    THE DEPOSIT IS THE NONZERO CELLS, WHICH IS NOT A COMPRESSION TRICK BUT THE THEOREM'S OWN SHAPE:
    *"store E as `q\\σ` against a producer model σ."* Here the producer model is the EMPTY σ — a fresh
    `new_sigma()` is all zeros, identical for everyone, so it need not be stored — and what is written
    is exactly the difference the accrual made. Measured on 154KB of his own body: 14% of cells are
    nonzero, so the deposit IS the residual against the anchor.

    ⚑ THE REVOLVE PATH IS NOT OPTIONAL AND IS WHY `ground` IS REQUIRED. The theorem, immediately
    before the storage corollary: *"detect when accumulated K_A is refuted by fresh interaction and
    GAP THE STALE KERNEL, seeding a revised one. Without that revolve path, 'accuracy improves at
    1/√n' silently becomes 'commits to its first misread at 1/√n.' Persistence buys stability only
    when paired with the ability to be wrong and know it."* So a σ is deposited UNDER THE IDENTITY OF
    THE GROUND IT WAS ACCRUED FROM, and `revive` refuses it when that ground has moved. A body that
    changed is fresh interaction refuting the old coverage — the change IS the refutation, and the
    honest answer is to gap the kernel and accrue a revised one, not to carry a model of a self that
    no longer exists.

    AND IT IS SCOPED, NEVER POOLED — the same corollary, measured: scoped-per-lens 3.31× against a
    global pool 3.14×, the pooled row named *"the forbidden cross-lens move"*, because *"pooling
    across lenses DILUTES the model."* One σ per ground, never merged. A caller's material dies with
    the crank by design; that seam is not courtesy, it is the tighter compression.
    """
    import native_json                                       # his own JSON, on the path
    import ark_io                                            # his own write(2)
    header = {"format": "ark-sigma-v3-delta-log", "ground": str(ground),
              "n_ctx": len(sigma.w), "mask": sigma.mask, "maxorder": sigma.maxorder,
              "bit_orders": list(sigma.bit_orders)}
    continuing = False
    prior_size = 0
    try:
        # The header decides whether this is the same sovereign delta lineage.  Receiving the
        # complete (potentially unbounded) ash merely to read that first relation rematerialized
        # every prior application at each deposit.  Receive only through the first newline.
        header_raw = bytearray()
        for chunk in ark_io.receive_chunks(path):
            newline = chunk.find(b"\n")
            header_raw += chunk if newline < 0 else chunk[:newline]
            if newline >= 0:
                break
        old = native_json.loads(bytes(header_raw).decode("utf-8"))
        prior_size = os.path.getsize(path)
        continuing = (old.get("format") == header["format"] and
                      str(old.get("ground")) == str(ground) and
                      int(old.get("n_ctx", -1)) == len(sigma.w) and
                      int(old.get("mask", -1)) == sigma.mask)
    except Exception:
        continuing = False

    # A v2 ash is migrated once.  Thereafter only cells changed since the last
    # successful deposit are appended: Lambda+ = Lambda union the application.
    if continuing:
        indices = sorted(sigma.dirty)
    else:
        indices = [(ci, i) for ci in range(len(sigma.w))
                   for i in sorted(set(sigma.w[ci]) | set(sigma.cnt[ci]) | set(sigma.rem[ci]))
                   if (sigma.w[ci].get(i, 0) or sigma.cnt[ci].get(i, 0)
                       or sigma.rem[ci].get(i, 0))]
    state = native_json.dumps({"hist": sigma.hist, "bitreg": sigma.bitreg, "c0": sigma.c0})
    body = bytearray(state.encode("utf-8") + b"\n")
    for ci, i in indices:
        body += (b"D" + bytes((ci,)) + int(i).to_bytes(4, "big")
                 + int(sigma.w[ci].get(i, 0)).to_bytes(4, "big", signed=True)
                 + int(sigma.cnt[ci].get(i, 0)).to_bytes(4, "big", signed=False)
                 + int(sigma.rem[ci].get(i, 0)).to_bytes(8, "big", signed=True))
    frame = b"F" + len(body).to_bytes(8, "big") + body
    if continuing:
        ark_io.give_file(path, frame, append=True)
        written = len(frame)
    else:
        prefix = native_json.dumps(header).encode("utf-8") + b"\n"
        ark_io.give_file(path, prefix + frame)
        written = len(prefix) + len(frame)
    # RETURNS WHAT IT DID, so the caller can LAND it. A write that returns nothing can only be
    # observed by looking at the file — which puts a reader's hand inside the organ to learn that
    # the organ ran (Noah, 2026-08-08: *"I'm a bit concerned that your hand needs to be in an organ
    # in order to know when Vigil begins to write"*). The cell count is the honest size of what was
    # learned: nonzero cells ARE the accrual, since a fresh σ is all zeros.
    capacity = sigma.capacity()
    page_advance = None
    if continuing and getattr(sigma, "page_store", None) is not None:
        try:
            from . import sigma_pages
            page_advance = sigma_pages.advance_deposit(
                sigma, path, frame=bytes(frame), prior_size=prior_size)
        except Exception as exc:
            # The append-only delta log is already authoritative.  A page-head refusal leaves the
            # next rise an explicit full-recovery derivation; it must never make the deposit vanish.
            page_advance = {"refused": "%s: %s" % (type(exc).__name__, exc)}
    sigma.dirty.clear()
    sigma.precision_opened = 0
    sigma.precision_witness = None
    receipt = {"bytes": written, "cells": capacity["occupied_buckets"],
               "delta_cells": len(indices), "capacity": capacity}
    if page_advance is not None:
        receipt["page_advance"] = page_advance
    return receipt


def revive(path, ground):
    """σ OUT OF THE ASH — or `None`, which is the revolve firing rather than a failure.

    Returns a σ restored to the deposited coverage when the ground identity matches, and `None` when
    it does not: the ground moved, so the accumulated kernel is refuted by that movement and is
    gapped. `None` is also what an absent or unreadable deposit gives — genesis from ∅, which is the
    same rule read twice (*"ash present → rise from ash; no ash → genesis from ∅"*), so the caller
    needs no branch for "first life" versus "refuted"."""
    import native_json
    import ark_io
    try:
        blob = ark_io.receive_file(path)
    except Exception:
        return None
    nl = blob.find(b"\n")
    if nl < 0:
        return None
    try:
        head = native_json.loads(blob[:nl].decode("utf-8"))
    except Exception:
        return None
    if str(head.get("ground")) != str(ground):
        return None                                          # the ground moved — gap the stale kernel
    bo = head.get("bit_orders") or ()
    stored_mask = int(head.get("mask", (1 << 18) - 1))
    tbits = (stored_mask + 1).bit_length() - 1
    sigma = _fc.new_predictor(maxorder=int(head.get("maxorder", 4)), use_match=False,
                              tbits=tbits,
                              use_bit_grain=tuple(bo) if bo else False)
    if len(sigma.w) != int(head.get("n_ctx", -1)) or sigma.mask != int(head.get("mask", -1)):
        return None                                          # a different substrate shape is not this σ
    body = blob[nl + 1:]
    if head.get("format") == "ark-sigma-v3-delta-log":
        off = 0
        try:
            while off < len(body):
                if body[off:off + 1] != b"F" or off + 9 > len(body):
                    return None
                size = int.from_bytes(body[off + 1:off + 9], "big")
                frame = body[off + 9:off + 9 + size]
                if len(frame) != size:
                    return None
                fnl = frame.find(b"\n")
                if fnl < 0:
                    return None
                state = native_json.loads(frame[:fnl].decode("utf-8"))
                pos = fnl + 1
                if (len(frame) - pos) % 22:
                    return None
                while pos < len(frame):
                    if frame[pos:pos + 1] != b"D":
                        return None
                    ci = frame[pos + 1]
                    i = int.from_bytes(frame[pos + 2:pos + 6], "big")
                    sigma.w[ci][i] = int.from_bytes(frame[pos + 6:pos + 10], "big", signed=True)
                    sigma.cnt[ci][i] = int.from_bytes(frame[pos + 10:pos + 14], "big", signed=False)
                    sigma.rem[ci][i] = int.from_bytes(frame[pos + 14:pos + 22], "big", signed=True)
                    pos += 22
                sigma.hist = int(state.get("hist", 0))
                sigma.bitreg = int(state.get("bitreg", 0))
                sigma.c0 = int(state.get("c0", 1))
                off += 9 + size
        except (IndexError, ValueError, OverflowError):
            return None
    elif head.get("format") == "ark-sigma-v2-residual-precision":
        off = 0
        try:
            while off < len(body):
                kind = body[off:off + 1]
                ci = body[off + 1]
                i = int.from_bytes(body[off + 2:off + 6], "big")
                if kind == b"B":
                    sigma.w[ci][i] = int.from_bytes(body[off + 6:off + 10], "big", signed=True)
                    sigma.cnt[ci][i] = int.from_bytes(body[off + 10:off + 14], "big", signed=True)
                    off += 14
                elif kind == b"R":
                    sigma.rem[ci][i] = int.from_bytes(body[off + 6:off + 14], "big", signed=True)
                    off += 14
                else:
                    return None
        except (IndexError, ValueError):
            return None
    else:
        if len(body) % 13:
            return None
        for off in range(0, len(body), 13):
            ci = body[off]
            i = int.from_bytes(body[off + 1:off + 5], "big")
            sigma.w[ci][i] = int.from_bytes(body[off + 5:off + 9], "big", signed=True)
            sigma.cnt[ci][i] = int.from_bytes(body[off + 9:off + 13], "big", signed=True)
    if head.get("format") != "ark-sigma-v3-delta-log":
        sigma.hist = int(head.get("hist", 0))
        sigma.bitreg = int(head.get("bitreg", 0))
        sigma.c0 = int(head.get("c0", 1))
    sigma.occupied_buckets = sum(1 for table in sigma.cnt for count in table if count)
    sigma.precision_axes_count = sum(1 for table in sigma.rem for value in table if value)
    sigma.dirty.clear()
    return sigma


def project(sigma, data):
    """P(Λ|q,h)'s residual — read `data` against the ACCRUED σ WITHOUT mutating it, and return ρ = the
    per-BYTE residual in F-native bits: how many bits σ could not predict away at each position. CARRIED
    per position — no threshold into "regions", no sum into a scalar (that is the collapse). Cheap positions
    are what σ folds (redundancy/markup); expensive positions are the residual (meaning), the seed of the
    next grain. Non-mutating so the same σ projects every passage identically (a PROJECTION, not accrual).
    `data` is bytes.

    Delegates to the codec's `project_delta` — the same F as `predict()`+`update()` per bit, with the hot
    loop inlined (no per-bit method calls to `_ctx_hashes`/`predict`/`update`/`_squash`), a delta-undo of
    only the touched table entries (~3% of the model) instead of a full 2.4M-entry snapshot, and F's own
    ln pre-derived into two 4096-entry cost tables. Same math, same residuals, same model state after —
    10–30× faster on the O(n²) genesis path. The codec's `snapshot()`/`restore()` stay available for
    callers that actually share a prelude across many blocks; this path was the only one paying the full
    copy for a one-shot read."""
    data = signal_bytes(data)
    return sigma.project_delta(data, _BIT_COST_1, _BIT_COST_0)


def emit_forward(sigma, nbytes, *, sample=False, rng=None):
    """THE INVERSE (anti-causal) LOOP — the codec's own predict()+update() run FORWARD, EMITTING the
    model's predicted bit instead of scoring a given one. Same F, other direction. Bits are MSB-first
    (the codec's c0 = (c0<<1)|bit), so the byte assembles the same way the reader consumes it. Mutates
    `sigma` (each emitted bit is accrued, exactly as a real bit would be), so callers pass a fork."""
    out = bytearray()
    for _ in range(nbytes):
        b = 0
        for _ in range(8):
            p = sigma.predict()                      # 12-bit P(bit = 1)
            bit = (1 if (rng.random() * 4096) < p else 0) if sample else (1 if p >= 2048 else 0)
            sigma.update(bit)
            b = (b << 1) | bit
        out.append(b)
    return bytes(out)



def generate(sigma, nbytes, *, sample=False, seed=0):
    """Emit a finite continuation from owned accrual without altering that accrual.

    The caller supplies the already accrued state. For successive carrier slices,
    retain a fork and call emit_forward on it; a byte boundary is not semantic
    completion. Generated state stays distinct from subsequently observed evidence.
    """
    import random
    return emit_forward(sigma.fork(), nbytes, sample=sample, rng=random.Random(seed))


def emit_keep_going(sigma, reach, rounds, *, sample=False, seed=0):
    """THE INVERSE RECURRENCE — emit_forward's keep-going form. generate() is ONE reach on a fork,
    leaving accrual whole; this does NOT fork: each round's reach is accrued into `sigma` (emit_forward
    mutates it), so the NEXT reach is natively conditioned on the residual the last one left. That is
    the operator recurring on its own emission — an observed motion's gap driving the next inverse
    generation, no halt term. The mover is the trajectory of σ's own confidence (mean |p−2048|/2048
    over each round's bits); dryness is READ OFF it, never declared. `sigma` is
    mutated (it carries the whole imagined motion at return); callers who must keep the accrual pass a
    fork. Returns a list of {round, bytes, mean_confidence, conf_delta, period}.

    THE FINISH IS AN ORBIT, NOT A SINGLE DELTA (register #1670, 2026-09-21): on some prefixes the
    emission returns to a prior round's bytes and cycles (period 2 observed: b'e nerati' / b'on of th'),
    and conf_delta then oscillates instead of collapsing — a reader stopping at one small delta
    declares dryness a round before it rises again. So each round also carries `period`: the smallest
    k ≥ 1 with bytes[r] == bytes[r−k] (the emission is a fixpoint of F^k), else None. A cycle is itself
    an observed finish (F^k = id on the emission) and is named as such — never a cap, never a floor;
    the caller reads dryness off the orbit (period held, or conf_delta flat over a window)."""
    import random
    rng = random.Random(seed)
    traj = []
    prev = None
    seen = []
    for r in range(rounds):
        out = bytearray()
        csum = 0.0
        nbits = 0
        for _ in range(reach):
            b = 0
            for _ in range(8):
                p = sigma.predict()
                bit = (1 if (rng.random() * 4096) < p else 0) if sample else (1 if p >= 2048 else 0)
                sigma.update(bit)
                csum += abs(p - 2048) / 2048.0
                nbits += 1
                b = (b << 1) | bit
            out.append(b)
        conf = csum / max(1, nbits)
        emitted = bytes(out)
        period = None
        for k in range(1, len(seen) + 1):            # smallest k: this round returned to round r−k
            if seen[-k] == emitted:
                period = k
                break
        traj.append({"round": r, "bytes": emitted, "mean_confidence": round(conf, 4),
                     "conf_delta": None if prev is None else round(abs(conf - prev), 4),
                     "period": period})
        seen.append(emitted)
        prev = conf
    return traj
