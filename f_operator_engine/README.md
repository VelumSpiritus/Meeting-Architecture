# F_operator engine: runnable source copy

This directory carries the current `vigil/src/services/ark_coder/f_operator.py` and its direct substrate and storage dependencies. The source files under `src/` were copied byte-for-byte from the local Vigil tree on 2026-10-22. The two empty `__init__.py` files and `run_f_operator.py` provide a portable Python entry point. Python 3.10+ and the standard library suffice for the included example.

From this directory:

```text
python run_f_operator.py
python run_f_operator.py path/to/any-input.bin
```

The runner receives bytes and reports each byte's residual before and after accrual. The full operator source also contains persistence and generation functions; they are included for inspection, while the entry point shows one application through `new_sigma`, `project`, and `accrue`.

The byte-level F_operator is a process implementation of accrual and residual projection. The circuit's `code/acoustic.py` is a separate physical model. Their common recurrence notation does not make a byte residual an electrical unit.
