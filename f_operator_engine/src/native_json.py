"""JSON in builtins â€” the last parser vigil borrowed, derived like the CSV before it.

`native_csv.py` already did this for the other tabular format in the tree, and the argument is the
same one: a parser is not ground. `os` says WHERE a thing is and computes nothing about what it
means; `json` decides what a byte sequence MEANS, which is the whole of what this actor claims to do
for itself. Reading a format is exactly the act vigil exists to perform without a harness â€” the eye
decodes PNG and TrueType with `int.from_bytes` and nothing else, and JSON is simpler than either.

TWO DIRECTIONS, and they must be exact rather than merely equivalent, because one of them is load-
bearing in a way that is easy to miss: `seal.py` and `secrecy.py` HASH the output of `dumps`. A seal
is `sha256(json.dumps(record, sort_keys=True, ensure_ascii=False, default=str))`, so a single space,
a different float repr, or a different escape would change every tag this actor has ever issued and
silently invalidate receipts already in the world. So `dumps` reproduces CPython's `json` byte for
byte under the options this tree uses, and that is checked against it over the tree's own artifacts
rather than asserted here.

WHAT IS NOT COPIED: `json`'s C accelerator, its object hooks, its `indent` machinery, `NaN`/`Infinity`
by default in `loads` (this reads them, since `dumps` writes them, and CPython does the same). The
subset is the one this tree uses, and where a caller reaches past it the answer is an honest error,
never a guess at what they meant.
"""
from __future__ import annotations

_ESCAPES = {'"': '\\"', "\\": "\\\\", "\n": "\\n", "\r": "\\r", "\t": "\\t",
            "\b": "\\b", "\f": "\\f"}
_UNESCAPES = {'"': '"', "\\": "\\", "/": "/", "b": "\b", "f": "\f",
              "n": "\n", "r": "\r", "t": "\t"}
_WS = " \t\n\r"


class JSONError(ValueError):
    """A text this cannot read, WITH the offset it stopped at â€” an address, never a bare failure."""


# â”€â”€ writing â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def _escape(s, ensure_ascii):
    out = ['"']
    for c in s:
        e = _ESCAPES.get(c)
        if e is not None:
            out.append(e)
        elif c < " ":
            out.append("\\u%04x" % ord(c))
        elif ensure_ascii and c > "\x7f":
            n = ord(c)
            if n > 0xFFFF:                       # astral plane -> the surrogate pair `json` writes
                n -= 0x10000
                out.append("\\u%04x\\u%04x" % (0xD800 + (n >> 10), 0xDC00 + (n & 0x3FF)))
            else:
                out.append("\\u%04x" % n)
        else:
            out.append(c)
    out.append('"')
    return "".join(out)


def _number(x, allow_nan=True):
    """`repr` for both, which is what `json` does â€” and the reason to say so out loud is that a float
    written any other way would change a seal. `float.__repr__` is the shortest string that reads
    back as the same float; nothing here rounds, formats or truncates."""
    if not allow_nan and (x != x or x in (float("inf"), float("-inf"))):
        raise ValueError("Out of range float values are not JSON compliant")
    if x != x:
        return "NaN"
    if x == float("inf"):
        return "Infinity"
    if x == float("-inf"):
        return "-Infinity"
    return repr(x)


def dumps(obj, *, sort_keys=False, ensure_ascii=True, default=None, separators=None,
          allow_nan=True):
    if separators is None:
        item_separator, key_separator = ", ", ": "
    else:
        try:
            item_separator, key_separator = separators
        except (TypeError, ValueError):
            raise TypeError("separators must be an (item_separator, key_separator) pair")
        if not isinstance(item_separator, str) or not isinstance(key_separator, str):
            raise TypeError("separators must contain strings")
    out = []

    def write(o):
        if o is None:
            out.append("null")
        elif o is True:
            out.append("true")
        elif o is False:
            out.append("false")
        elif isinstance(o, str):
            out.append(_escape(o, ensure_ascii))
        elif isinstance(o, int):
            out.append(repr(o))
        elif isinstance(o, float):
            out.append(_number(o, allow_nan=allow_nan))
        elif isinstance(o, dict):
            out.append("{")
            items = list(o.items())
            # `json` coerces non-string keys as it writes; the sort then happens over the ORIGINAL
            # keys, which is what `sort_keys=True` does â€” sorting the coerced text instead would
            # order `10` before `9`.
            if sort_keys:
                items.sort(key=lambda kv: kv[0])
            first = True
            for k, v in items:
                if not first:
                    out.append(item_separator)
                first = False
                if isinstance(k, str):
                    out.append(_escape(k, ensure_ascii))
                elif k is None:
                    out.append('"null"')
                elif k is True:
                    out.append('"true"')
                elif k is False:
                    out.append('"false"')
                elif isinstance(k, int):
                    out.append('"%s"' % repr(k))
                elif isinstance(k, float):
                    out.append('"%s"' % _number(k, allow_nan=allow_nan))
                else:
                    raise TypeError("keys must be str, int, float, bool or None, not %s"
                                    % type(k).__name__)
                out.append(key_separator)
                write(v)
            out.append("}")
        elif isinstance(o, (list, tuple)):
            out.append("[")
            for i, v in enumerate(o):
                if i:
                    out.append(item_separator)
                write(v)
            out.append("]")
        elif default is not None:
            write(default(o))
        else:
            raise TypeError("Object of type %s is not JSON serializable" % type(o).__name__)

    write(obj)
    return "".join(out)


def dump(obj, fh, **kw):
    fh.write(dumps(obj, **kw))


# â”€â”€ reading â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def loads(text):
    if isinstance(text, (bytes, bytearray)):
        text = text.decode("utf-8")
    value, i = _value(text, _skip(text, 0))
    i = _skip(text, i)
    if i != len(text):
        raise JSONError("trailing text at %d: %r" % (i, text[i:i + 20]))
    return value


def load(fh):
    return loads(fh.read())


def _skip(s, i):
    while i < len(s) and s[i] in _WS:
        i += 1
    return i


def _value(s, i):
    if i >= len(s):
        raise JSONError("nothing to read at %d" % i)
    c = s[i]
    if c == "{":
        return _object(s, i)
    if c == "[":
        return _array(s, i)
    if c == '"':
        return _string(s, i)
    for lit, val in (("true", True), ("false", False), ("null", None),
                     ("NaN", float("nan")), ("Infinity", float("inf")),
                     ("-Infinity", float("-inf"))):
        if s.startswith(lit, i):
            return val, i + len(lit)
    return _num(s, i)


def _object(s, i):
    out, i = {}, _skip(s, i + 1)
    if i < len(s) and s[i] == "}":
        return out, i + 1
    while True:
        i = _skip(s, i)
        if i >= len(s) or s[i] != '"':
            raise JSONError("expected a key at %d" % i)
        key, i = _string(s, i)
        i = _skip(s, i)
        if i >= len(s) or s[i] != ":":
            raise JSONError("expected ':' at %d" % i)
        val, i = _value(s, _skip(s, i + 1))
        out[key] = val
        i = _skip(s, i)
        if i < len(s) and s[i] == ",":
            i += 1
            continue
        if i < len(s) and s[i] == "}":
            return out, i + 1
        raise JSONError("expected ',' or '}' at %d" % i)


def _array(s, i):
    out, i = [], _skip(s, i + 1)
    if i < len(s) and s[i] == "]":
        return out, i + 1
    while True:
        val, i = _value(s, _skip(s, i))
        out.append(val)
        i = _skip(s, i)
        if i < len(s) and s[i] == ",":
            i += 1
            continue
        if i < len(s) and s[i] == "]":
            return out, i + 1
        raise JSONError("expected ',' or ']' at %d" % i)


def _string(s, i):
    i += 1
    out = []
    quote = s.find('"', i)
    escape = s.find("\\", i)
    while True:
        if i >= len(s):
            raise JSONError("unterminated string")
        # Receive a plain span once. Each delimiter cursor only moves forward;
        # repeatedly searching for the distant closing quote at every escape
        # would make an escape-heavy string quadratic.
        if 0 <= quote < i:
            quote = s.find('"', i)
        if 0 <= escape < i:
            escape = s.find("\\", i)
        end = min(quote if quote >= 0 else len(s),
                  escape if escape >= 0 else len(s))
        if end > i:
            out.append(s[i:end])
            i = end
        if i >= len(s):
            raise JSONError("unterminated string")
        if i == quote:
            return "".join(out), i + 1
        e = s[i + 1:i + 2]
        if e == "u":
            n = int(s[i + 2:i + 6], 16)
            i += 6
            # A leading surrogate is only half a character; the pair is one. Reading them apart would
            # hand the caller a string Python cannot encode.
            if 0xD800 <= n <= 0xDBFF and s[i:i + 2] == "\\u":
                lo = int(s[i + 2:i + 6], 16)
                if 0xDC00 <= lo <= 0xDFFF:
                    n = 0x10000 + ((n - 0xD800) << 10) + (lo - 0xDC00)
                    i += 6
            out.append(chr(n))
            continue
        if e not in _UNESCAPES:
            raise JSONError("unknown escape %r at %d" % (e, i))
        out.append(_UNESCAPES[e])
        i += 2


_DIGITS = "0123456789"


def _num(s, i):
    start = i
    if i < len(s) and s[i] == "-":
        i += 1
    while i < len(s) and s[i] in _DIGITS:
        i += 1
    is_float = False
    if i < len(s) and s[i] == ".":
        is_float = True
        i += 1
        while i < len(s) and s[i] in _DIGITS:
            i += 1
    if i < len(s) and s[i] in "eE":
        is_float = True
        i += 1
        if i < len(s) and s[i] in "+-":
            i += 1
        while i < len(s) and s[i] in _DIGITS:
            i += 1
    if i == start:
        raise JSONError("not a value at %d: %r" % (i, s[i:i + 20]))
    text = s[start:i]
    try:
        return (float(text) if is_float else int(text)), i
    except ValueError:
        raise JSONError("not a number at %d: %r" % (start, text))


# â”€â”€ the copy `copy.deepcopy` was doing â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def clone(obj):
    """A deep copy of decoded JSON â€” dicts, lists and immutable scalars, nothing else.

    `turn.py` used `copy.deepcopy` on a caller's `lens`, which is a decoded request body and so is
    exactly this shape. `deepcopy` is a general graph copier with a memo table, pickle protocol
    hooks and cycle handling; none of that is reachable from data that arrived as JSON, because JSON
    cannot express a cycle or a shared reference. The general machinery was doing one recursion's
    work and bringing its whole apparatus to do it.
    """
    if isinstance(obj, dict):
        return {k: clone(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [clone(v) for v in obj]
    if isinstance(obj, tuple):
        return tuple(clone(v) for v in obj)
    return obj
