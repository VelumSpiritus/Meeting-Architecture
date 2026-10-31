# Reproduce the model and inspect the evidence

Start with EVIDENCE.md for the photographed 0.33 to 0.61 V Vpp speaker-free series, wiring chronology, equations, and analysis. The original photographs are under crystal_scope_sources/. The speaker-free topology reconstruction, earlier drawings, proposed inverter drawing, and source notes are under schematics/. The exact final breadboard holes and inherited lamp/return connections need bench confirmation. The short source-transcript excerpts are at data/build_chronology_excerpt.md.

Requires Python 3.10 or later. The simulation path uses only the Python standard library. From this folder:

    cd code
    python simulate.py --beats 100
    python simulate_battery_form.py
    python simulate_carry.py
    python simulate_acoustic.py --beats 300 --speaker-gain 0
    python ablate_recurrence.py

The commands write fresh results under code/runs/. The battery-form run writes a JSON summary and reports its assumed mechanical input, capture efficiencies, buffer, converter and battery-acceptance boundary. The acoustic command is a topology comparison with speaker gain set to zero; it is not a wiring-level model of the photographed apparatus.

For additional circuit simulations, begin with simulations/README.md. The source and controls are under code/; saved outputs from the original runs are under simulations/results/.
The simulations model the same reciprocal coupling physics as the photographed circuit — piezoelectric forcing, mechanical/electrical energy transfer through the quartz-solution interface, and downstream charge capture. They use standard literature material values and assumed geometry rather than parameters curve-fit to reproduce specific photographed voltages, which makes the correspondence independently testable: run the simulation, compare its output to the scope photographs, and measure the gap yourself.
