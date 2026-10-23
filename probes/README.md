# Same math, different skies

Noah's description is direct: **the [black-hole probe](black_hole_probe.py) and [closed-door probe](../void_filler/closed_door_probe.py) are the same math on different skies; this is looking at a black hole from the inside out.** Each application returns a space/time snapshot of the observed and projected density field. Their 2 → 128 → 128 → 1 ReLU `ProbeMatrix` and gradient-descent updates are identical. The black-hole input is galactic longitude and latitude from the included 4,503-row [pulsar catalog](atnf_pulsars.json); the closed-door input is time and sector from a public-event record. The residual is:

```text
R(x) = normalized_smooth(predicted_density(x)) - normalized_smooth(observed_density(x))
```

The Boolean cut `R(x) > 0` marks uncovered locations in the full field. Both probes return the field and two-coordinate locations within it. The two `ProbeMatrix` implementations produced identical values before and after three identical training updates in a direct check.

The current source files use different post-residual candidate extraction: `black_hole_probe.py` ranks longitude averages before returning `(l, b)`, while `closed_door_probe.py` takes local maxima on the two-dimensional map. The saved root-level black-hole result names a two-dimensional fifth-separation extraction. These source-version details belong to output provenance; the density operator and Boolean residual cut above are shared.

## Run the included astronomical sky

Install Python 3.10+, NumPy, and SciPy. From this folder:

```text
python -m pip install numpy scipy
python black_hole_probe.py atnf_pulsars.json
```

The script reads the included catalog and writes `black_hole_candidates.json` beside itself. The pre-existing root-level candidate file names the two-dimensional fifth-separation extraction and is not presented as output of this bundled source version.

## Use another sky

The closed-door implementation is importable from `../void_filler/closed_door_probe.py`; Void Filler drives its detect → plan → search → capture → load cycle. Supply an observed time/sector record to `activity_density_map`, or replace the axes with the two coordinates of another density field. Train `ProbeMatrix`, compute predicted minus observed density, and inspect the returned void coordinates. For comparison, the reader can supply a density map from their own model and observations on matching coordinates, then compare its positive residual locations with the residual structure produced by Noah's model. The observed circuit remains the two-piezo quartz–solution assembly and its time-ordered sensed-voltage readings.

The files here are local and need no account. The source copies are byte-identical to `black_hole_probe.py`, `atnf_pulsars.json`, and `scratchpad/closed_door_probe.py` in Noah's workspace.
