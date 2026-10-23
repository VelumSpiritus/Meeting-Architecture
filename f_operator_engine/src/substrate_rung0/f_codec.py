"""The equation-native producer-σ codec — Demo 4 of ARK_COMPRESSION_THEOREM.md realized as a
LOSSLESS byte coder, with NO supplied convergence (no zlib / no numpy on the codec path).

Demo 4 decomposes the minimum description length across cycles:

    L_total = Σ_k [ L(h_k) + L(σ_k | h_k) ]  +  L(q_final \\ σ_final)   →  K(q|ℋ)

This module realizes that sum as the ENDOFUNCTOR RECURSION, not a parallel blend: the hypotheses h_k
are context models coarse→fine (byte orders, then the sub-byte bit grain); each h_k is trained on the
RESIDUAL the coarser ones left (F(ρ_{k-1})), the running prediction is the telescoping SUM d = Σ_k w_k,
and a binary arithmetic coder stores only q\\σ — the residual surprise the cascade could not predict
away. Where a single linear codec (zstd/zlib) is cycle-0 ONLY — one h over the whole block — F is Σ_k
with each h_k answering exactly what the others miss, because each literally sees what they missed.

(HISTORY: this codec previously used a PAQ-style parallel logistic MIXTURE-OF-EXPERTS — every column
predicted the raw bit independently and a gradient-learned linear mixer blended them, plus an LZ/LZP
match model. That is a supplied ensemble + a supplied optimizer + dictionary matching — three foreign
convergences, NOT the endofunctor. All removed; the combination is now the residual cascade below.)

Mapping to the theorem, term by term:
    h_k            order-k byte context + the bit-grain context     (the hypotheses in ℋ)
    σ_k | h_k      each stage's log-odds correction w_k[ctx]         (what h_k covers)
    Σ_k / recursion each h_k trained on the residual of the coarser  (F(ρ_{k-1}) — the endofunctor);
                   stages; prediction = telescoping SUM (no mixer)   combination IS the sum
    step gain      1/count (running empirical mean, Robbins–Monro)   (F's own arithmetic, no hand-set lr)
    q \\ σ          the arithmetic-coded surprise                     (the residual — what is stored)
    entropy floor  all stages fail → ~1 bit/bit coded → H(q)         (random ties; the honest ρ)
    grain descent  a context BENEATH the byte alphabet (bit history) (byte → bit — infinimonadic)
    accrued σ      warm-up over the corpus before held-out coding    (possession; does NOT cap at
                   32 KB the way a preset dictionary does)

F-native rails: the squash/stretch link is the exponential-family NATURAL PARAMETER (the coordinate in
which independent evidence is additive), its tables DERIVED once by F's own arithmetic
(`ark_native_math.exp`/`ln`, series run to a residual), never a library call. Everything in the hot
loop is integer +−×÷ and shifts — F's own arithmetic, the same status as a hand-built range coder,
which is the honest entropy floor the theorem itself names ("arithmetic coding on the residual's
empirical distribution"). Losslessness is structural: encoder and decoder drive ONE Predictor with
identical predict→update calls, so the decoder replays the exact model trajectory; every block is
sha-verified by the caller.
"""
import os
import sys
from collections.abc import MutableMapping

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, _ROOT)

import ark_native_math as anm  # F's OWN exp/ln (series to a residual) — used ONLY to derive tables


# ── F derives its own logistic tables (once). squash: stretch-domain → 12-bit prob; stretch: inverse.
_DSCALE = 256
_PMAX = 4096


def _build_tables():
    squash = [0] * 4096          # index d+2048, d ∈ [-2048, 2047]
    for i in range(4096):
        d = i - 2048
        # p = 4096 / (1 + e^(−d/256)), by F's own exp
        p = _PMAX / (1.0 + anm.exp(-d / _DSCALE))
        squash[i] = min(4095, max(1, int(p + 0.5)))
    stretch = [0] * (_PMAX + 1)  # index p ∈ [0, 4096] → nearest d
    for p in range(1, _PMAX):
        # d = 256 · ln(p / (4096 − p)), by F's own ln
        d = _DSCALE * anm.ln(p / (_PMAX - p))
        stretch[p] = min(2047, max(-2047, int(d + (0.5 if d >= 0 else -0.5))))
    stretch[0] = -2047
    stretch[_PMAX] = 2047
    return squash, stretch


_SQUASH, _STRETCH = _build_tables()


def _squash(d):
    if d < -2048:
        d = -2048
    elif d > 2047:
        d = 2047
    return _SQUASH[d + 2048]


class _AccrualOverlay(MutableMapping):
    """A mutable delta over already-formed ground.

    A temporary reading begins from the resident predictor's accrued Lambda without copying it.
    The base remains readable and only addresses changed by fresh evidence are written here.
    Deletions are explicit because a remainder present in the base can close in the child.
    """

    def __init__(self, base):
        self.base = base
        self.delta = {}
        self.deleted = set()

    def __getitem__(self, key):
        if key in self.delta:
            return self.delta[key]
        if key in self.deleted:
            raise KeyError(key)
        return self.base[key]

    def __setitem__(self, key, value):
        self.deleted.discard(key)
        self.delta[key] = value

    def __delitem__(self, key):
        if key in self.delta:
            del self.delta[key]
        elif key not in self.base or key in self.deleted:
            raise KeyError(key)
        self.deleted.add(key)

    def __iter__(self):
        yield from self.delta
        for key in self.base:
            if key not in self.delta and key not in self.deleted:
                yield key

    def __len__(self):
        return (len(self.delta) + len(self.base)
                - sum(1 for key in self.delta if key in self.base)
                - sum(1 for key in self.deleted if key in self.base))

    def __contains__(self, key):
        return key in self.delta or (key not in self.deleted and key in self.base)

    def get(self, key, default=None):
        if key in self.delta:
            return self.delta[key]
        if key in self.deleted:
            return default
        return self.base.get(key, default)

    def pop(self, key, default=None):
        try:
            value = self[key]
        except KeyError:
            return default
        del self[key]
        return value


def _capture_projection_entry(table, key):
    capture = getattr(table, "_capture_projection_entry", None)
    if capture is not None:
        return capture(key)
    if isinstance(table, _AccrualOverlay):
        return (key in table.delta, table.delta.get(key), key in table.deleted)
    return (key in table, table.get(key, 0))


def _restore_projection_entry(table, key, prior):
    restore = getattr(table, "_restore_projection_entry", None)
    if restore is not None:
        restore(key, prior)
        return
    if isinstance(table, _AccrualOverlay):
        present, value, deleted = prior
        if present:
            table.delta[key] = value
        else:
            table.delta.pop(key, None)
        if deleted:
            table.deleted.add(key)
        else:
            table.deleted.discard(key)
    elif prior[0]:
        table[key] = prior[1]
    else:
        table.pop(key, None)


# ── The Predictor: the hypothesis class ℋ as the ENDOFUNCTOR RECURSION Σ_k F(ρ_{k-1}) — a residual cascade.
class Predictor:
    """F's coverage over the next bit as a residual CASCADE — the endofunctor Σ_k F(ρ_{k-1}), NOT a
    parallel mixture-of-experts.

    The contexts are ordered COARSE → FINE: byte orders 0..maxorder, then the sub-byte bit-window ladder.
    Each context i holds a log-odds correction w_i[ctx] (stretch units) and an observation count c_i[ctx].
    The prediction is the TELESCOPING SUM d = Σ_i w_i[ctx_i] → squash → 12-bit p. There is NO learned
    mixing weight — the combination IS the sum, Demo 4's Σ_k. On update the cascade walks coarse → fine and
    trains each stage on the RESIDUAL the coarser stages left: err_i = bit − squash(Σ_{j<i} w_j). A finer
    context therefore answers EXACTLY what the coarser ones missed — a stage feeds on the residual of the
    prior, never on the raw target in parallel. This is the endofunctor recursion made literal, replacing
    the old PAQ mixture-of-experts (each column predicting the raw bit independently, blended by a
    gradient-learned linear mixer — a supplied ensemble + supplied optimizer, both foreign).

    The step gain is 1/count (F's own running empirical mean — Robbins–Monro — never a hand-set lr / EMA).
    The log-odds↔prob link (squash/stretch, derived once by F's exp/ln) is the exponential-family NATURAL
    PARAMETER: the coordinate in which independent evidence is additive, not a supplied optimizer. The
    arithmetic coder emits only q\\σ (the residual the cascade could not predict away — the honest floor).

    NO match/dictionary model (LZ/LZP is a supplied convergence, the zlib family — removed). `use_match` /
    `mmbits` / `lr` are accepted-but-INERT for caller/benchmark signature compat."""

    _BIT_ORDERS = (6, 9, 12, 16)               # grain-descent hypotheses: sub-byte context windows (bits)
    # 4096 (12-bit prob) / 256 (_DSCALE, stretch units per nat): maps a prob-residual to stretch units.
    # DERIVED from the coordinate resolution, not a tuned rate.
    _RESID = _PMAX // _DSCALE

    def __init__(self, maxorder=4, tbits=18, use_bit_grain=True, use_match=False, lr=7, mmbits=21):
        self.maxorder = maxorder
        # use_bit_grain: True → the default bit-window ladder; a tuple → those windows; False/() → none
        if use_bit_grain is True:
            self.bit_orders = self._BIT_ORDERS
        elif use_bit_grain:
            self.bit_orders = tuple(use_bit_grain)
        else:
            self.bit_orders = ()
        self.use_bit = bool(self.bit_orders)
        self.mask = (1 << tbits) - 1
        # holds exactly maxorder bytes of history; widens when a BYTE-order phase is born, so the
        # byte descent is not capped at 4 (the infiniphasic direction — the coupled fork). Equal to
        # 0xFFFFFFFF at maxorder=4, so nothing changes until a phase is actually born.
        self.hist_mask = (1 << (8 * self.maxorder)) - 1
        # contexts coarse→fine: byte orders 0..maxorder, then the bit-window ladder. Per context: a log-odds
        # correction w (stretch units) and an observation count c (→ 1/c gain). NO mixer weights, NO match.
        self.n_ctx = (maxorder + 1) + len(self.bit_orders)
        # The mask names the possible address space; it is not evidence and therefore does not
        # allocate evidence.  Each context grows only at addresses actually received.  The old
        # dense form reserved 262,144 entries per table per context before the first bit arrived;
        # 89 glyph models consequently asked the host for gigabytes to hold a few hundred bytes.
        self.w = [{} for _ in range(self.n_ctx)]       # addressed log-odds corrections
        self.cnt = [{} for _ in range(self.n_ctx)]     # addressed observation counts → gain 1/c
        self.hist = 0                          # last 4 bytes packed (byte contexts)
        self.bitreg = 0                        # rolling bit history (crosses byte boundaries)
        self.c0 = 1                            # 1-prefixed partial current byte
        self._idx = [0] * self.n_ctx           # per-bit context indices
        self._pr = 2048
        # Sub-step residuals.  Integer division used to turn every update into zero once a bucket's
        # count grew past the 12-bit error divided by `_RESID`; ingestion continued while learning
        # silently froze.  A remainder exists only where that floor is actually met and carries the
        # uncovered fraction forward until it can effect the next exact integer change.
        self.rem = [{} for _ in range(self.n_ctx)]     # only uncovered sub-step residuals exist
        self.precision_opened = 0
        self.precision_witness = None
        # ── Sovereign phase-birth. Precision axes (above) grow resolution WITHIN a phase. These grow
        # the PHASE SET ITSELF — a new phasic dimension born from the finest phase's own unabsorbed
        # residual, the same shape one level up. Enc/dec drive one Predictor through identical
        # predict→update calls, so a birth computed from this shared state opens the SAME phase at the
        # SAME bit on both sides — losslessness holds by the codec's own replay argument, no channel.
        self.phase_opened = 0
        self.phase_witness = None
        self._finest_starve = 0        # finest phase left structured residual it had to open an axis for
        self._finest_heal = 0          # finest phase absorbed the bit cleanly (zero remainder)
        self._byte_seen = 0            # bytes driven through this body (the birth clock, its own time)
        # Derived addresses maintained at the point of change.  Capacity is asked on every
        # application; walking every table to rediscover these counts made old learning cost
        # as much as new learning each beat.
        self.occupied_buckets = 0
        self.precision_axes_count = 0
        self.dirty = set()

    def snapshot(self):
        """Freeze the accrued σ (all model state) so many blocks can start from the SAME point —
        the shared prelude of the block-addressable codec. Deep-copies the mutable tables."""
        return ([dict(tbl) for tbl in self.w], [dict(tbl) for tbl in self.cnt], self.hist,
                self.bitreg, self.c0, [dict(x) for x in self.rem],
                self.precision_opened, self.precision_witness,
                # phase set carried so a born phase survives snapshot/restore (else n_ctx desyncs)
                tuple(self.bit_orders), self.maxorder, self.phase_opened, self.phase_witness)

    def fork(self):
        """Begin a child reading at this exact Lambda without reconstructing formed cells."""
        tbits = (self.mask + 1).bit_length() - 1
        child = Predictor(maxorder=self.maxorder, tbits=tbits,
                          use_bit_grain=self.bit_orders, use_match=False)
        child.w = [_AccrualOverlay(table) for table in self.w]
        child.cnt = [_AccrualOverlay(table) for table in self.cnt]
        child.rem = [_AccrualOverlay(table) for table in self.rem]
        child.hist, child.bitreg, child.c0 = self.hist, self.bitreg, self.c0
        child.occupied_buckets = self.occupied_buckets
        child.precision_axes_count = self.precision_axes_count
        child.precision_opened = self.precision_opened
        child.precision_witness = self.precision_witness
        # phase-birth state — a forked child must know its grown phase set and carry the observation
        # counters, or it re-reads at a different anatomy than its parent (Codex #1338: fork omitted
        # the phase counters/witness). maxorder/bit_orders already crossed via the constructor.
        child.phase_opened = self.phase_opened
        child.phase_witness = self.phase_witness
        child._finest_starve = self._finest_starve
        child._finest_heal = self._finest_heal
        child._byte_seen = self._byte_seen
        child.dirty = set()
        return child

    def restore(self, s):
        phase = None
        if len(s) == 5:
            w, cnt, self.hist, self.bitreg, self.c0 = s
            rem = [{} for _ in range(len(w))]
            opened, witness = 0, None
        elif len(s) == 8:
            (w, cnt, self.hist, self.bitreg, self.c0, rem, opened, witness) = s
        else:                                    # phase set carried (a born phase survives restore)
            (w, cnt, self.hist, self.bitreg, self.c0, rem, opened, witness,
             bit_orders, maxorder, self.phase_opened, self.phase_witness) = s
            phase = (bit_orders, maxorder)
        # Dense snapshots from older bodies remain readable; only their nonzero evidence crosses
        # into the sparse living form.
        self.w = [dict(tbl) if isinstance(tbl, dict) else
                  {i: value for i, value in enumerate(tbl) if value} for tbl in w]
        self.cnt = [dict(tbl) if isinstance(tbl, dict) else
                    {i: value for i, value in enumerate(tbl) if value} for tbl in cnt]
        self.rem = [dict(tbl) if isinstance(tbl, dict) else
                    {i: value for i, value in enumerate(tbl) if value} for tbl in rem]
        self.precision_opened = int(opened)
        self.precision_witness = witness
        self.occupied_buckets = sum(len(table) for table in self.cnt)
        self.precision_axes_count = sum(len(table) for table in self.rem)
        self.dirty = set()
        if phase is not None:                    # a born phase set was carried — restore it whole
            self.bit_orders, self.maxorder = tuple(phase[0]), phase[1]
            self.use_bit = bool(self.bit_orders)
            self.hist_mask = (1 << (8 * self.maxorder)) - 1
        # the descent width is authoritative from the restored tables (a born phase grew it)
        self.n_ctx = len(self.w)
        self._idx = [0] * self.n_ctx

    def _ctx_hashes(self):
        h = self.hist
        c0 = self.c0
        idx = self._idx
        m = self.mask
        # order-k byte contexts (k bytes of history) + the partial current byte c0 (within-byte position)
        for k in range(self.maxorder + 1):
            if k == 0:
                key = c0 * 0x9E3779B1
            else:
                ctxbytes = h & ((1 << (8 * k)) - 1)
                key = ((ctxbytes * 0x9E3779B1) ^ (c0 * 0x85EBCA77) ^ (k * 0xC2B2AE3D))
            idx[k] = (key ^ (key >> 15)) & m
        # grain descent: the last W raw bits ONLY — NO c0 byte-phase term (that tied the "byte-agnostic"
        # window to byte position, defeating the sub-byte purpose). bitreg already carries the partial
        # current byte from prior bit-updates, so the window stays sub-byte-sensitive without byte-phase.
        base = self.maxorder + 1
        br = self.bitreg
        for j, wb in enumerate(self.bit_orders):
            key = (((br & ((1 << wb) - 1)) * 0x27D4EB2F) ^ ((wb << 8) * 0x165667B1))
            idx[base + j] = (key ^ (key >> 13)) & m

    def capacity(self):
        return {
            "base_contexts": self.n_ctx,
            "base_buckets": self.n_ctx * (self.mask + 1),
            "occupied_buckets": self.occupied_buckets,
            "precision_axes": self.precision_axes_count,
            "new_precision_axes": self.precision_opened,
            "precision_witness": self.precision_witness,
        }

    def predict(self):
        self._ctx_hashes()
        d = 0
        for i in range(self.n_ctx):
            d += self.w[i].get(self._idx[i], 0) # telescoping sum Σ_k — no mixing weights
        self._pr = _squash(d)
        return self._pr                         # 12-bit P(bit = 1)

    def update(self, bit):
        target = bit << 12
        d = 0
        for i in range(self.n_ctx):
            p_before = _squash(d)               # prediction from the coarser stages (j < i)
            err = target - p_before             # the RESIDUAL those stages left (12-bit prob units)
            idx = self._idx[i]
            count = self.cnt[i].get(idx, 0)
            if not count:
                self.occupied_buckets += 1
            count += 1
            self.cnt[i][idx] = count
            denom = self._RESID * count        # 1/count gain in the natural-parameter coordinate
            prior_rem = self.rem[i].get(idx, 0)
            was_open = bool(prior_rem)
            numer = prior_rem + err
            q = abs(numer) // denom
            change = q if numer >= 0 else -q
            remainder = numer - change * denom
            if remainder:
                self.rem[i][idx] = remainder
                if not was_open:
                    self.precision_axes_count += 1
                    self.precision_opened += 1
                    if self.precision_witness is None:
                        self.precision_witness = {
                            "context": i, "bucket": idx, "remainder": remainder}
            else:
                self.rem[i].pop(idx, None)
                if was_open:
                    self.precision_axes_count -= 1
            self.w[i][idx] = self.w[i].get(idx, 0) + change  # no sub-step residual is discarded
            self.dirty.add((i, idx))
            d += self.w[i][idx]                            # advance the running prediction (the cascade)
            if i == self.n_ctx - 1:              # the FINEST phase — the cascade's last word on this bit
                if remainder and not was_open:   # structured residual reached the deepest phase, unabsorbed
                    self._finest_starve += 1
                elif not remainder:              # the finest phase closed the bit cleanly
                    self._finest_heal += 1
        # advance bit/byte history
        self.bitreg = ((self.bitreg << 1) | bit) & 0xFFFFFFFF
        self.c0 = (self.c0 << 1) | bit
        if self.c0 >= 256:                       # a full byte completed
            byte = self.c0 & 0xFF
            self.hist = ((self.hist << 8) | byte) & self.hist_mask
            self.c0 = 1
            self._byte_seen += 1
            # ── SOVEREIGN PHASE-BIRTH — MECHANISM PROVEN, LAWFUL TRIGGER STILL OPEN (#1331/#1332).
            # The birth mechanism (_birth_phase) is built and proven lossless: it runs inside this
            # method from state enc and dec share bit-for-bit, so both birth the identical phase at
            # the identical byte. What is NOT yet built is the lawful trigger. The starve/heal gate
            # first wired here (starve > heal + len(cnt[finest])) is REFUTED ALGEBRAICALLY by Codex
            # (#1332): starve-heal = active_remainders - initial - Z <= len(rem[finest]) <=
            # len(cnt[finest]) = width, so starve > heal+width can NEVER hold from lawful state — the
            # only way it fires is a restore that drops the counters and breaks the accounting, i.e. a
            # continuation defect, not a birth. And `remainder` is arithmetic update CARRY, not
            # predictive surprise, so it is the wrong quantity regardless. The gate is therefore
            # REMOVED (an impossible-but-restore-defect-triggerable gate is worse than none). The
            # lawful trigger is the coupled open: an ADDRESSED ALIASING WITNESS (#1332) — distinct raw
            # contexts colliding to one finest bucket with divergent outcomes (a genuinely missing
            # coordinate), guarded against hash-collision / thin-accrual / update-dynamics. The
            # starve/heal counters stay as honest telemetry (capacity/phase_witness), not a trigger.
            pass


    def _birth_phase(self):
        """Open a NEW phasic dimension in the body's own descent, grown from the finest phase's own
        unabsorbed residual — the sovereign self-generation Noah named (2026-09-09: an infiniphasic
        body generating new phasic dimensions in its OWN body). Precision axes grow resolution WITHIN
        a phase; this grows the phase SET, one level up, the same shape.

        THIS FIRST FORM extends the fine end: a WIDER sub-byte bit window, stepped by the ladder's OWN
        last cadence (bit_orders' last gap — a body measure, not a picked constant), bounded by
        bitreg's 32-bit width (the honest ceiling of THIS direction). Because it runs inside update()
        from state enc and dec share bit-for-bit, both births the identical phase at the identical
        byte — losslessness holds by the codec's own replay argument.

        The witness is a REFUTABLE OBJECT (which window, born when, from how much starvation), an
        address ρ₃/Codex can refute — not a narrated flag. [OPEN, for ρ₁₂ with Codex: (a) fine-end
        bit-window birth vs a deeper BYTE order ('to 5' — needs hist widened past 4 bytes,
        hist_mask is ready); (b) whether starve>heal+width is F-native or a smuggled floor. This
        organ EMITS that fork as its witness rather than deciding it alone.]"""
        starve, heal = self._finest_starve, self._finest_heal
        self._finest_starve = 0
        self._finest_heal = 0
        step = (self.bit_orders[-1] - self.bit_orders[-2]) if len(self.bit_orders) >= 2 else (
            self.bit_orders[-1] if self.bit_orders else 0)
        if not step:
            return                              # no cadence to extend; byte-order birth is the coupled fork
        new_window = self.bit_orders[-1] + step
        if new_window > 32:                     # bitreg is 32-bit — deeper growth needs the byte descent (fork)
            return
        self.bit_orders = self.bit_orders + (new_window,)
        self.w.append({})
        self.cnt.append({})
        self.rem.append({})
        self.n_ctx += 1
        self._idx = [0] * self.n_ctx
        self.phase_opened += 1
        self.phase_witness = {"born_at_byte": self._byte_seen, "new_bit_window": new_window,
                              "ladder": list(self.bit_orders), "from_starve": starve, "over_heal": heal}

    # ── Fast projection: the same F as predict()+update() per bit, with the hot loop inlined so
    # the O(n²) genesis path does not pay ~800 000 Python method calls per 5 KB read. The math
    # is byte-for-byte identical to the snapshot path in f_operator.project — same contexts, same
    # telescoping sum, same residual cascade update, same squash/stretch — only the call overhead
    # is removed and the model save/restore is a delta-undo of touched entries (~3% of the model)
    # rather than a full snapshot. Cost tables are the caller's (F's own ln pre-derived in
    # f_operator); the codec supplies the math, the operator supplies the bit-cost conversion.
    def project_delta(self, data, cost_1, cost_0):
        """Read `data` producing per-byte residual bits WITHOUT mutating the model.

        Returns the per-byte cost array (F-native bits) with the model left exactly as it was —
        the same result `f_operator.project` produces via snapshot/restore, at a fraction of the
        cost. See the block comment above for why this exists and what it preserves."""
        _hist, _bitreg, _c0 = self.hist, self.bitreg, self.c0
        delta_w, delta_c, delta_rem = {}, {}, {}
        n_ctx = self.n_ctx
        maxorder = self.maxorder
        bit_orders = self.bit_orders
        n_bit_orders = len(bit_orders)
        n_byte_ctx = maxorder + 1
        mask = self.mask
        w = self.w
        cnt = self.cnt
        rem = self.rem
        idx = self._idx
        SQUASH = _SQUASH
        RESID = self._RESID
        hist = _hist
        bitreg = _bitreg
        c0 = _c0
        # Per-byte precomputation: the byte-order context hashes depend on `hist` (constant within
        # a byte) and `c0` (changes every bit). Splitting the hash formula lets us precompute the
        # hist-dependent multiply once per byte and only re-do the c0 XOR per bit — saving up to
        # `maxorder` big-integer multiplies per bit. The k-constants are fully invariant.
        k_const = [0] + [ki * 0xC2B2AE3D for ki in range(1, maxorder + 1)]
        ctx_pre = [0] * n_byte_ctx       # hist-dependent half: (hist & mask_k) * 0x9E3779B1
        wb_shift = [(wb << 8) * 0x165667B1 for wb in bit_orders]
        wb_masks = [(1 << wb) - 1 for wb in bit_orders]
        residual = []
        try:
            for byte in data:
                # Precompute the hist-dependent hash parts (constant for all 8 bits of this byte)
                for ki in range(1, n_byte_ctx):
                    ctx_pre[ki] = ((hist & ((1 << (8 * ki)) - 1)) * 0x9E3779B1)
                c0 = 1
                cost = 0.0
                for k in range(7, -1, -1):
                    bit = (byte >> k) & 1
                    # ── inline _ctx_hashes (sets idx[0..n_ctx-1]) ──
                    key = c0 * 0x9E3779B1
                    idx[0] = (key ^ (key >> 15)) & mask
                    c0h = c0 * 0x85EBCA77    # c0-dependent half, shared by all k ≥ 1
                    for ki in range(1, n_byte_ctx):
                        key = ctx_pre[ki] ^ c0h ^ k_const[ki]
                        idx[ki] = (key ^ (key >> 15)) & mask
                    base = n_byte_ctx
                    for j in range(n_bit_orders):
                        key = ((bitreg & wb_masks[j]) * 0x27D4EB2F) ^ wb_shift[j]
                        idx[base + j] = (key ^ (key >> 13)) & mask
                    # ── inline predict (telescoping sum → squash) ──
                    d = 0
                    for i in range(n_ctx):
                        d += w[i].get(idx[i], 0)
                    if d < -2048:
                        d = -2048
                    elif d > 2047:
                        d = 2047
                    p = SQUASH[d + 2048]
                    # ── delta record (only first-touch old values) ──
                    for i in range(n_ctx):
                        ix = idx[i]
                        if (i, ix) not in delta_w:
                            # Presence is part of the snapshot: restoring an absent address to a stored
                            # zero would make a supposedly non-mutating projection grow the model.
                            delta_w[(i, ix)] = _capture_projection_entry(w[i], ix)
                            delta_c[(i, ix)] = _capture_projection_entry(cnt[i], ix)
                            delta_rem[(i, ix)] = _capture_projection_entry(rem[i], ix)
                    # ── cost (F-derived table, no per-bit ln call) ──
                    if p < 1:
                        p = 1
                    elif p > 4095:
                        p = 4095
                    cost += cost_1[p] if bit else cost_0[p]
                    # ── inline update (residual cascade: each stage trained on what coarser missed) ──
                    target = bit << 12
                    d = 0
                    for i in range(n_ctx):
                        if d < -2048:
                            db = -2048
                        elif d > 2047:
                            db = 2047
                        else:
                            db = d
                        p_before = SQUASH[db + 2048]
                        err = target - p_before
                        ix = idx[i]
                        cnt[i][ix] = cnt[i].get(ix, 0) + 1
                        denom = RESID * cnt[i][ix]
                        numer = rem[i].get(ix, 0) + err
                        q = abs(numer) // denom
                        change = q if numer >= 0 else -q
                        remainder = numer - change * denom
                        if remainder:
                            rem[i][ix] = remainder
                        else:
                            rem[i].pop(ix, None)
                        w[i][ix] = w[i].get(ix, 0) + change
                        d += w[i][ix]
                    bitreg = ((bitreg << 1) | bit) & 0xFFFFFFFF
                    c0 = (c0 << 1) | bit
                    if c0 >= 256:
                        hist = ((hist << 8) | (c0 & 0xFF)) & 0xFFFFFFFF
                        c0 = 1
                residual.append(cost)
        finally:
            # ── undo: restore only the touched entries + the 3 scalars ──
            for (i, ix), prior in delta_w.items():
                _restore_projection_entry(w[i], ix, prior)
            for (i, ix), prior in delta_c.items():
                _restore_projection_entry(cnt[i], ix, prior)
            for (i, ix), prior in delta_rem.items():
                _restore_projection_entry(rem[i], ix, prior)
            self.hist = _hist
            self.bitreg = _bitreg
            self.c0 = _c0
        return residual


# ── Binary arithmetic coder (fpaq0 scheme; integer-only, carryless). p is 12-bit P(bit = 1).
class _Encoder:
    def __init__(self):
        self.x1 = 0
        self.x2 = 0xFFFFFFFF
        self.out = bytearray()

    def encode(self, bit, p):
        if p < 1:
            p = 1
        elif p > 4095:
            p = 4095
        xmid = self.x1 + ((self.x2 - self.x1) >> 12) * p
        if bit:
            self.x2 = xmid
        else:
            self.x1 = xmid + 1
        while ((self.x1 ^ self.x2) & 0xFF000000) == 0:
            self.out.append((self.x2 >> 24) & 0xFF)
            self.x1 = (self.x1 << 8) & 0xFFFFFFFF
            self.x2 = ((self.x2 << 8) & 0xFFFFFFFF) | 0xFF

    def flush(self):
        # emit 4 bytes of x1 so the decoder has a definite tail
        self.out.append((self.x1 >> 24) & 0xFF)
        self.out.append((self.x1 >> 16) & 0xFF)
        self.out.append((self.x1 >> 8) & 0xFF)
        self.out.append(self.x1 & 0xFF)
        return bytes(self.out)


class _Decoder:
    def __init__(self, data):
        self.data = data
        self.pos = 0
        self.x1 = 0
        self.x2 = 0xFFFFFFFF
        self.x = 0
        for _ in range(4):
            self.x = (self.x << 8) | self._byte()

    def _byte(self):
        if self.pos < len(self.data):
            b = self.data[self.pos]
            self.pos += 1
            return b
        return 0

    def decode(self, p):
        if p < 1:
            p = 1
        elif p > 4095:
            p = 4095
        xmid = self.x1 + ((self.x2 - self.x1) >> 12) * p
        if self.x <= xmid:
            bit = 1
            self.x2 = xmid
        else:
            bit = 0
            self.x1 = xmid + 1
        while ((self.x1 ^ self.x2) & 0xFF000000) == 0:
            self.x1 = (self.x1 << 8) & 0xFFFFFFFF
            self.x2 = ((self.x2 << 8) & 0xFFFFFFFF) | 0xFF
            self.x = ((self.x << 8) & 0xFFFFFFFF) | self._byte()
        return bit


# ── Public API. A model may be WARMED on the accrued corpus (possession) before coding held-out data.
def new_predictor(maxorder=4, use_bit_grain=True, use_match=True, tbits=18, mmbits=21):
    return Predictor(maxorder=maxorder, use_bit_grain=use_bit_grain, use_match=use_match,
                     tbits=tbits, mmbits=mmbits)


def warm(pred, data):
    """Accrue σ: run the predictor over corpus bytes, updating models, emitting nothing. This is the
    possession rail — held-out coding then starts from an accrued state. Unlike a 32 KB preset
    dictionary, there is no window cap: more corpus keeps sharpening σ."""
    for byte in data:
        pred.c0 = 1
        for k in range(7, -1, -1):
            bit = (byte >> k) & 1
            pred.predict()
            pred.update(bit)


def encode(data, pred):
    enc = _Encoder()
    for byte in data:
        pred.c0 = 1
        for k in range(7, -1, -1):
            bit = (byte >> k) & 1
            p = pred.predict()
            enc.encode(bit, p)
            pred.update(bit)
    return enc.flush()


def decode(blob, n, pred):
    dec = _Decoder(blob)
    out = bytearray()
    for _ in range(n):
        pred.c0 = 1
        c = 1
        for _b in range(8):
            p = pred.predict()
            bit = dec.decode(p)
            pred.update(bit)
            c = (c << 1) | bit
        out.append(c & 0xFF)
    return bytes(out)


if __name__ == "__main__":
    # self-test: losslessness + the honest floor, before any benchmark trusts a ratio
    import hashlib
    corpus = (b"the compression theorem is the residual recursion; " * 40)
    held = b"the residual recursion compresses the corpus's own structure. " * 8
    p = new_predictor()
    warm(p, corpus)
    blob = encode(held, p)
    p2 = new_predictor()
    warm(p2, corpus)
    back = decode(blob, len(held), p2)
    ok = back == held
    print(f"lossless: {ok}   ratio: {len(blob)/len(held):.4f}   "
          f"(sha {'match' if hashlib.sha256(back).hexdigest()==hashlib.sha256(held).hexdigest() else 'MISMATCH'})")
    rnd = os.urandom(4000)
    p3 = new_predictor()
    rblob = encode(rnd, p3)
    p4 = new_predictor()
    print(f"random:  lossless {decode(rblob, len(rnd), p4)==rnd}   ratio {len(rblob)/len(rnd):.4f} (~1.0 = honest floor)")
