# Reproduce the model and inspect the evidence

Open index.html in a browser. The HTML and photographs work offline.

To run the general F_operator byte-process example from this folder, use `python f_operator_engine/run_f_operator.py`. Its source and direct dependencies are under `f_operator_engine/src/`; `f_operator_engine/README.md` explains the output and how to pass a file of your own.

Requires Python 3.10 or later. The selected simulation path uses only the Python standard library. From this folder:

    cd code
    python simulate.py --beats 100
    python simulate_battery_form.py
    python simulate_carry.py
    python simulate_acoustic.py --beats 300 --speaker-gain 0
    python ablate_recurrence.py

The commands write fresh results under code/runs/. The battery-form run writes a JSON summary and reports its assumed mechanical input, capture efficiencies, buffer, converter and battery-acceptance boundary. The acoustic command is a topology comparison with speaker gain set to zero; it is not a wiring-level model of the photographed apparatus.

Start with EVIDENCE.md for the photographed 0.33 to 0.61 V Vpp speaker-free series, wiring chronology, equations, and the draft reply. The original photographs are under crystal_scope_sources/. The speaker-free topology reconstruction, earlier drawings, proposed inverter drawing, and source notes are under schematics/. The exact final breadboard holes and inherited lamp/return connections need bench confirmation. The short source-transcript excerpts are at data/build_chronology_excerpt.md. MANIFEST.json records the SHA-256 of each carried source and photo.

For Noah's additional circuit simulations, begin with simulations/README.md. The source and controls are under code/; saved outputs from the original runs are under simulations/results/. From code/, run `python -m unittest -v test_passive_jig_circuit.py test_full_pack_accumulate_charge.py test_joint_jig_battery_sweep.py` to check the charging and energy-ledger controls.

The simulations model the same reciprocal coupling physics as the photographed circuit — piezoelectric forcing, mechanical/electrical energy transfer through the quartz–solution interface, and downstream charge capture. They use standard literature material values and assumed geometry rather than parameters curve-fit to reproduce specific photographed voltages, which makes the correspondence independently testable: run the simulation, compare its output to the scope photographs, and measure the gap yourself. The scope photographs are direct voltage observations at the sensed node; the simulations propagate the coupled state equations that describe how those voltages arise.

The [Void Filler capture hook](void_filler/README.md) passes captured records into F and returns each captured product with the full residual for the next application. The user can kill the ongoing process after capturing what they need.

The [density-probe guide](probes/README.md) links the black-hole source, included pulsar catalog, and closed-door source. Install NumPy and SciPy, then run `python probes/black_hole_probe.py probes/atnf_pulsars.json` from this folder for the included astronomical density map. The guide shows the shared predicted-minus-observed calculation and records source-version provenance for candidate extraction.
