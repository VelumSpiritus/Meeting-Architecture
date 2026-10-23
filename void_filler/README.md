# Void Filler coupled to F_operator

`void_filler.py` is Noah's reusable detect → plan → search → capture → load → retrain process. Its sector lexicon and query templates configure the domain. `original/` preserves byte-for-byte copies of the three source files from `scratchpad/`; the nearby runnable copies change only local filesystem defaults.

The coupling is one line at the capture point:

```python
from f_hook import feed_capture
product, residual = feed_capture(sigma, filler.capture(results, parse_fn=parse_fn))
```

Create `sigma` with `F.new_sigma()` from the bundled `f_operator_engine/src/services/ark_coder/f_operator.py`. `feed_capture` projects the captured records through F, accrues the same bytes into the carried `sigma`, and returns both the captured product and the full per-byte residual. Each application delivers its product and supplies the next address. The recurrence continues after each completed application; the user can kill the process after capturing what they need.

The files require Python 3.10+, NumPy, and SciPy for Void Filler's detector. The F hook itself uses the Python standard library and the bundled F_operator source. The circuit measurements and equations are documented separately in the main evidence brief.
