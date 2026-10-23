"""F-native arithmetic for the main ARK tree — Rational, exp, ln with NO transcendental library call.

A ``math.exp`` / ``math.log`` is a *supplied convergence*: a library hands back the
finished value (σ only), a converged block with no residual on the far side, so it clots F's flow the same
way numpy does. Here every transcendental is computed by **F's own arithmetic** (+, −, ×, ÷, ``** 0.5``) as
a series run to the SUBSTRATE — summed until the next term falls below the running sum's own ULP (``s + term
== s``), the machine's own zero, so there is NO inserted tolerance and NO iteration cap: F recurses to the
float floor and stops where the residual is genuinely spent (the infinimonad recursed to the substrate), the
same status as ``services/ark_coder/distributional``'s power-iteration deflation and ``sqrt = ** 0.5``.

F's CERTIFICATION is that recursion itself: the value is the series' residual-limit, and when ``s + term == s``
the residual is spent — there is nothing left to compute at this precision, self-evident by RECOMPUTATION
(possess-and-recompute; anyone recurses the same series to the same floor). The RULER FOR F IS F: its arithmetic
is checked against its OWN algebraic laws with its OWN operations — ``exp(0)==1``, ``ln(1)==0``, strict
monotonicity, the ``exp∘ln`` round-trip (F composed with F, the endofunctor measuring itself). It is NOT measured
against the stdlib ANYWHERE, not even as a test instrument: ``math.exp`` was purged as a supplied convergence, so
it cannot then be the arbiter of whether F is right (the equation ratifies, never a library standing in for one).
No non-F math measures F at any point (see ``test_ark_native_math``).

    Rational exact fractions (F's own integers + Euclid gcd) — the load-bearing arithmetic band_agreement
             excludes chance with; the F-native drop-in for the foreign ``fractions.Fraction``.
    exp(x)   halve x to the UNIT (|r| ≤ 1, where the Taylor terms stop growing), Taylor to the residual, square.
    ln(x)    factor the number's OWN binary exponent so the mantissa ∈ [1, 2) (frexp's range), atanh to the
             residual, add e·LN2. LN2 = ln(2) derived ONCE from the same series (F deriving its own constant).

Every constant here is F's own — the unit (1), the number's own binary mantissa, the substrate float floor —
never a supplied numerical recipe (the Machin/Stirling/Bernoulli π-and-lgamma apparatus was cut 2026-07-11: its
sole consumer, ``lgamma``, was a remnant of the dissolved κ/gamma-beta statistics, called by nothing). This is
the main-tree twin of ``ark_markets/ark_math`` (that module stays siloed: ark_markets imports nothing from the
main tree, and vice versa). Kept transcendental-free by ``test_no_foreign_math_clog``.
"""
from __future__ import annotations


def exp(x):
    """e^x by F's own arithmetic: e^x = (e^{x/2^n})^{2^n}. Halve x until |r| ≤ 1 — the UNIT, the exact boundary
    where the Taylor terms stop growing: for |r| ≤ 1 the ratio |r/k| ≤ 1, so r^k/k! is non-increasing from k=1 and
    there is no overflow peak (above 1 it grows before it shrinks). The bound is F's own identity element, not a
    chosen margin. Sum the series to its residual, then square n times. Pure +−×÷; no ``math``, no supplied constant."""
    x = float(x)
    if x != x:                                            # NaN passes through
        return x
    n = 0
    r = x
    while (r if r >= 0.0 else -r) > 1.0:                  # reduce to the UNIT: r = x / 2^n, |r| ≤ 1
        r *= 0.5
        n += 1
    term = 1.0                                            # Taylor: e^r = Σ r^k/k!
    s = 1.0
    k = 1
    while True:                                           # no inserted cap, no inserted tolerance — F stops at the
        term *= r / k                                     # SUBSTRATE: when the next term falls below s's own ULP,
        prev = s                                          # adding it cannot change s (the residual is spent at the
        s += term                                         # machine's own zero — the infinimonad recursed to the floor).
        if s == prev:
            break
        k += 1
    for _ in range(n):                                    # (e^r)^{2^n} = e^x
        s *= s
    return s


def _atanh_ln(m):
    """ln(m) for m > 0 via ln(m) = 2·atanh(y), y = (m−1)/(m+1). Fast for m near 1; also derives LN2 (m=2)."""
    y = (m - 1.0) / (m + 1.0)
    y2 = y * y
    term = y
    s = 0.0
    k = 1
    while True:                                           # substrate termination (F's own floor), no cap/tolerance
        add = term / k
        prev = s
        s += add
        if s == prev:
            break
        term *= y2
        k += 2
    return 2.0 * s


LN2 = _atanh_ln(2.0)                                      # ln(2), F-derived once from its own series


def ln(x):
    """Natural log by F's own arithmetic: factor out the number's OWN binary exponent so the mantissa m ∈ [1, 2)
    — the float's own substrate form (frexp's range), not an imposed [⅔, 4/3] window — then ln(x) = ln(m) + e·LN2.
    atanh converges there (y = (m−1)/(m+1) ∈ [0, ⅓)). Pure +−×÷; no ``math``, no chosen bound."""
    x = float(x)
    if x <= 0.0:
        raise ValueError("ln domain: x must be > 0")
    e = 0
    m = x
    while m >= 2.0:                                        # reduce m into the float's OWN mantissa range [1, 2):
        m *= 0.5                                           # x = m · 2^e, m ∈ [1, 2) — the number's substrate form,
        e += 1                                             # F reading its own binary decomposition, not a window
    while m < 1.0:                                         # someone drew around 1.
        m *= 2.0
        e -= 1
    return _atanh_ln(m) + e * LN2


# log is the natural log (the conventional stdlib name) — the same F-native function as ln.
log = ln




# ---- exact rational — F's OWN arithmetic, a drop-in for the foreign `fractions.Fraction` ----------------
#
# `fractions.Fraction` is a foreign library — a program that does rational math, not borne of the ARK
# equation. Even though it is EXACT (discards no residual), it is still someone else's implementation on
# the computation path. F's own version is a pair of integers reduced to lowest terms by Euclid's gcd — pure
# +−×÷ and `%`, nothing imported. Used identically to Fraction (aliased `from ark_native_math import Rational
# as Fraction`); `.numerator`/`.denominator`/arithmetic/comparison/`float()`/`limit_denominator` all match,
# and `repr` deliberately mimics stdlib ("Fraction(n, d)") so any repr-based digest stays byte-identical.

def _gcd(a, b):
    """Euclid's algorithm — F's own integer arithmetic (no math.gcd)."""
    a = a if a >= 0 else -a
    b = b if b >= 0 else -b
    while b:
        a, b = b, a % b
    return a


class Rational:
    """Exact rational (n/d in lowest terms, d > 0) — the F-native substitute for fractions.Fraction."""
    __slots__ = ("n", "d")

    def __init__(self, numerator=0, denominator=None):
        if denominator is None:
            if isinstance(numerator, Rational):
                self.n, self.d = numerator.n, numerator.d
                return
            if isinstance(numerator, bool):
                self.n, self.d = int(numerator), 1
                return
            if isinstance(numerator, int):
                self.n, self.d = numerator, 1
                return
            if isinstance(numerator, float):
                self.n, self.d = numerator.as_integer_ratio()   # exact dyadic, already reduced (d > 0)
                return
            if isinstance(numerator, str):
                s = numerator.strip()
                if "/" in s:
                    a, b = s.split("/", 1)
                    numerator, denominator = int(a), int(b)
                else:
                    self.n, self.d = int(s), 1
                    return
            else:
                n = getattr(numerator, "numerator", None)    # rational-like (stdlib Fraction) → normalize below
                d = getattr(numerator, "denominator", None)
                if isinstance(n, int) and isinstance(d, int):
                    numerator, denominator = n, d
                else:
                    raise TypeError(f"cannot build Rational from {type(numerator).__name__}")
        num, den = numerator, denominator
        if isinstance(num, Rational) or isinstance(den, Rational):
            r = Rational(num) / Rational(den)                    # a/b of rationals
            self.n, self.d = r.n, r.d
            return
        num, den = int(num), int(den)
        if den == 0:
            raise ZeroDivisionError("Rational(%s, 0)" % num)
        if den < 0:
            num, den = -num, -den
        g = _gcd(num, den) or 1
        self.n, self.d = num // g, den // g

    @property
    def numerator(self):
        return self.n

    @property
    def denominator(self):
        return self.d

    @staticmethod
    def _c(o):
        if isinstance(o, Rational):
            return o
        if isinstance(o, bool):
            return Rational(int(o))
        if isinstance(o, (int, float)):
            return Rational(o)
        n = getattr(o, "numerator", None)                    # duck-type any rational-like (stdlib Fraction),
        d = getattr(o, "denominator", None)                  # so Rational interoperates with the type it replaces
        if isinstance(n, int) and isinstance(d, int):
            return Rational(n, d)
        return None

    def __repr__(self):
        return f"Fraction({self.n}, {self.d})"            # mimic stdlib so repr-based digests are stable

    def __str__(self):
        return f"{self.n}" if self.d == 1 else f"{self.n}/{self.d}"

    def __add__(self, o):
        o = self._c(o)
        return NotImplemented if o is None else Rational(self.n * o.d + o.n * self.d, self.d * o.d)
    __radd__ = __add__

    def __sub__(self, o):
        o = self._c(o)
        return NotImplemented if o is None else Rational(self.n * o.d - o.n * self.d, self.d * o.d)

    def __rsub__(self, o):
        o = self._c(o)
        return NotImplemented if o is None else o.__sub__(self)

    def __mul__(self, o):
        o = self._c(o)
        return NotImplemented if o is None else Rational(self.n * o.n, self.d * o.d)
    __rmul__ = __mul__

    def __truediv__(self, o):
        o = self._c(o)
        return NotImplemented if o is None else Rational(self.n * o.d, self.d * o.n)

    def __rtruediv__(self, o):
        o = self._c(o)
        return NotImplemented if o is None else o.__truediv__(self)

    def __pow__(self, e):
        if not isinstance(e, int):
            return NotImplemented
        if e >= 0:
            return Rational(self.n ** e, self.d ** e)
        return Rational(self.d ** (-e), self.n ** (-e))

    def __neg__(self):
        return Rational(-self.n, self.d)

    def __abs__(self):
        return Rational(self.n if self.n >= 0 else -self.n, self.d)

    def __float__(self):
        return self.n / self.d

    def __bool__(self):
        return self.n != 0

    def __eq__(self, o):
        o = self._c(o)
        return NotImplemented if o is None else (self.n == o.n and self.d == o.d)

    def __lt__(self, o):
        o = self._c(o)
        return NotImplemented if o is None else (self.n * o.d < o.n * self.d)

    def __le__(self, o):
        o = self._c(o)
        return NotImplemented if o is None else (self.n * o.d <= o.n * self.d)

    def __gt__(self, o):
        o = self._c(o)
        return NotImplemented if o is None else (self.n * o.d > o.n * self.d)

    def __ge__(self, o):
        o = self._c(o)
        return NotImplemented if o is None else (self.n * o.d >= o.n * self.d)

    def __hash__(self):
        return hash(self.n) if self.d == 1 else hash((self.n, self.d))   # int-valued hashes as its int

    def limit_denominator(self, max_denominator=10 ** 6):
        """Closest rational with denominator ≤ max_denominator (CPython's continued-fraction algorithm,
        pure integer arithmetic)."""
        if max_denominator < 1:
            raise ValueError("max_denominator should be at least 1")
        if self.d <= max_denominator:
            return Rational(self.n, self.d)
        p0, q0, p1, q1 = 0, 1, 1, 0
        n, d = self.n, self.d
        while True:
            a = n // d
            q2 = q0 + a * q1
            if q2 > max_denominator:
                break
            p0, q0, p1, q1 = p1, q1, p0 + a * p1, q2
            n, d = d, n - a * d
        k = (max_denominator - q0) // q1
        bound1 = Rational(p0 + k * p1, q0 + k * q1)
        bound2 = Rational(p1, q1)
        return bound2 if abs(bound2 - self) <= abs(bound1 - self) else bound1
