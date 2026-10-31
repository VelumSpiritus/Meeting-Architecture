"""Small dense matrix organ for the three-mode quartz body.

Only built-in arithmetic is used.  The body needs one 9x9 solve at genesis and
matrix-vector products thereafter; a general numerical package would be a
supplied engine much larger than the problem.
"""

from __future__ import annotations


def matrix(rows):
    out = [[float(value) for value in row] for row in rows]
    if out and any(len(row) != len(out[0]) for row in out):
        raise ValueError("ragged matrix")
    return out


def zeros(rows, columns):
    return [[0.0 for _ in range(columns)] for _ in range(rows)]


def identity(size):
    return [[1.0 if row == column else 0.0 for column in range(size)] for row in range(size)]


def transpose(a):
    return [list(column) for column in zip(*a)] if a else []


def add(a, b):
    return [[left + right for left, right in zip(arow, brow)] for arow, brow in zip(a, b)]


def subtract(a, b):
    return [[left - right for left, right in zip(arow, brow)] for arow, brow in zip(a, b)]


def scale(value, a):
    return [[value * item for item in row] for row in a]


def multiply(a, b):
    bt = transpose(b)
    return [[sum(left * right for left, right in zip(row, column)) for column in bt] for row in a]


def matvec(a, vector):
    return [sum(left * right for left, right in zip(row, vector)) for row in a]


def dot(left, right):
    return sum(a * b for a, b in zip(left, right))


def diagonal(values):
    values = [float(value) for value in values]
    return [[value if row == column else 0.0 for column, value in enumerate(values)]
            for row in range(len(values))]


def inverse_diagonal(values):
    values = [float(value) for value in values]
    if any(value == 0.0 for value in values):
        raise ValueError("zero diagonal has no inverse")
    return diagonal([1.0 / value for value in values])


def block(rows):
    """Join a rectangular grid of matrices."""
    output = []
    for block_row in rows:
        height = len(block_row[0])
        if any(len(part) != height for part in block_row):
            raise ValueError("block-row heights differ")
        for inner_row in range(height):
            joined = []
            for part in block_row:
                joined.extend(part[inner_row])
            output.append(joined)
    return output


def solve(a, b):
    """Solve A X = B by partial-pivot Gaussian elimination.

    There is no chosen tolerance or iteration bound: the finite matrix fixes
    the number of eliminations, and only an exact zero pivot names singularity.
    """
    n = len(a)
    if n == 0 or any(len(row) != n for row in a):
        raise ValueError("A must be a non-empty square matrix")
    if len(b) != n:
        raise ValueError("A and B row counts differ")
    width = len(b[0]) if b else 0
    if any(len(row) != width for row in b):
        raise ValueError("ragged B")
    augmented = [list(a[row]) + list(b[row]) for row in range(n)]

    for column in range(n):
        pivot = max(range(column, n), key=lambda row: abs(augmented[row][column]))
        if augmented[pivot][column] == 0.0:
            raise ValueError("singular matrix")
        if pivot != column:
            augmented[column], augmented[pivot] = augmented[pivot], augmented[column]
        pivot_value = augmented[column][column]
        augmented[column] = [value / pivot_value for value in augmented[column]]
        for row in range(n):
            if row == column:
                continue
            factor = augmented[row][column]
            if factor == 0.0:
                continue
            augmented[row] = [value - factor * pivot_item
                              for value, pivot_item in zip(augmented[row], augmented[column])]
    return [row[n:] for row in augmented]
