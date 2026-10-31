# Quartz–piezo circuit: evidence package

22 October 2026. This packet brings together the working theory's equations, simulations, physical assembly, and measurement record. The built, speaker-free circuit shows a rising sensed Vpp under a nominally constant 5 V supply. The original photographs and runnable code carry the result.

The [build photograph](crystal_scope_sources/build_photo.png) shows the physical setup as it sat for the entire ten-hour measurement. The circuit was not touched, moved, or modified during the run. The E10 filament bulb remained in the series path. The ground wire runs from the wall receptacle's earth ground directly into the salt solution — the electrolyte is earth-grounded.

**What this packet establishes:** In the speaker-free circuit, the photographed sensed Vpp rises from 0.33 to 0.61 V under a nominal 5 V supply. The reciprocal equations below provide a piezoelectric and electrical-storage model for examining that response; their numerical parameters are not fitted to this breadboard. The circuit's spatial arrangement and time-ordered voltage readings are the shared observable.

The [circuit simulation trail](simulations/README.md) carries runnable charging-jig and battery-coupling simulations, their saved outputs, and explicit no-input, diode-loss, and energy-closure controls. These null cases are applications of the equations themselves: zero mechanical input yields zero modeled charge; diode loss reduces held energy; the energy ledger closes.

## The built experiment

- The crystal is a **28 g quartz rock** immersed in salt solution. The geometry and mass record is included at [code/crystal/observations.jsonl](code/crystal/observations.jsonl).
- The original [Figma whiteboard](https://www.figma.com/file/PVCwILeP1i65cee6fr8bTY?type=whiteboard) and [v2 drawing](schematics/crystal_circuit_v2.svg) show an earlier speaker-output configuration. The speaker was subsequently removed and a **drive piezo** was installed beneath the rock, facing the sensing piezo. The **longitudinal 0.33 → 0.61 V Vpp series** was recorded in this **two-piezo, no-speaker configuration**. The [speaker-free topology reconstruction](schematics/crystal_circuit_speaker_free_reconstruction.svg), [complete earlier drawing](schematics/crystal_circuit_complete.svg), and [unbuilt inverter proposal](schematics/crystal_circuit_self_sustaining.svg) are included. [Drawing notes](schematics/README.md) distinguish recorded connections from inherited details awaiting bench confirmation.
- The PAM8403 module and its 5 V supply remained connected during that run. The inverter replacement shown in `crystal_circuit_self_sustaining.svg` was **not built**. The module's role in this result is the wired electrical drive path and adjustable constraint on the drive piezo. No audio speaker, sound-amplification claim, or measured voltage-gain claim belongs to the longitudinal result.
- The physical path being tested is **drive-piezo electrical perturbation → mechanical/ionic coupling through salt solution and the quartz rock → sensing-piezo electrical response → circuit return**. The DSO read the sensing path. The exact node-by-node final wiring belongs beside the original v2 drawing when sharing the experiment.

The [dated transcript excerpts](data/build_chronology_excerpt.md) place the change at 2026-10-19 05:44–05:49 UTC: Noah called the preceding photo "Before the extra piezo" and then described the second piezo under the crystal. Its subsequent measurements are the two-piezo series. The earlier October 18 scope series belongs to the earlier configuration and is not pooled with it.

## Photographed result

The original attachments were recovered from the author's source upload directory and copied byte-for-byte into `crystal_scope_sources/`. Upload-file times establish submission order, not camera exposure time.

| Configuration and image | Recorded display | SHA-256 |
|---|---|---|
| Two piezos, [12:48 AM image](crystal_scope_sources/8719a4f5-image.jpg), immediately after the speaker-to-piezo change | Vmax **0.16 V**, Vpp **0.33 V**, Vrms 0.03 V, displayed cycle 8.000 ms; 200 mV vertical, 200 ms horizontal | `2d90a84e51451a04437adce16eca95d4eabc7cf389cdbcd86671bfbbbd8a1563` |
| Two piezos, [12:50 AM image](crystal_scope_sources/33238142-image.jpg) | Vmax **0.18 V**, Vpp **0.35 V**, Vrms 0.12 V, displayed cycle 8.000 ms; 200 mV vertical, 200 ms horizontal | `da1bc7c063911a9147ee3bc6b5757407236bee45d7b99b39085820d35e91bae4` |
| Two piezos, [2:20 AM image](crystal_scope_sources/e6ab644b-image.jpg) | Vmax **0.30 V**, Vpp **0.47 V**, Vrms 0.10 V, displayed cycle 8.000 ms; 500 mV vertical, 200 ms horizontal | `de0187107f44012d602faffce734419cd5352129142c377dd839c7ffb7bcfbe8` |
| Two piezos, [10:30 AM image](crystal_scope_sources/67b51fe5-image.jpg) | Vmax **0.32 V**, Vpp **0.61 V**, Vrms 0.08 V, displayed cycle 8.000 ms; same display scales | `1718ff3ff50a78206c45bc5bfd8e33237dfd56a7a41c79140d4410b0be4911af` |

The speaker-free series begins at **0.33 V Vpp** and reaches **0.61 V Vpp** by the 10:30 AM image: **ΔVpp = +0.28 V** over roughly ten hours. The 2:20 AM reading is a later point in this series, not its baseline. The nested eight-hour comparison gives **ΔVpp = +0.14 V** and **ΔVmax = +0.02 V** at the displayed scope node. The waveform visibly changes from a dense oscillatory trace to more separated pulses. The earliest photographs use a 200 mV vertical display scale; the 2:20 and 10:30 AM pair both use 500 mV. All four show a 200 ms horizontal scale and displayed cycle of 8.000 ms. Noah states in the [included excerpt](data/build_chronology_excerpt.md) that the reader was unchanged. These are discrete readings; the endpoint differences do not establish a constant growth rate between photos.

The earlier [0.11 V Vmax image](crystal_scope_sources/cd33e69c-image.jpg) and [0.20 V Vmax image](crystal_scope_sources/037e89d4-image.jpg) preserve a separate pre-swap comparison. They are **not** evidence of the later two-piezo time series. The older transcript also reports a 0.12 → 0.20 V first-hour comparison, but the directly recovered early photo reads 0.11 V, so the packet uses photographed values when citing image evidence.

## Physics stated directly

The 5 V supply is an existing charge source. A fixed supply voltage does **not** prohibit charging: current can transfer charge into a capacitive element until its state approaches the operating condition set by the drive and losses. For a fixed linear capacitor at its own terminals, **Q = CV**, **I = dQ/dt**, and **U = ½CV²**. A constant 5 V at the supply does not imply that the sensing node or each piezo terminal is held at 5 V. Thus a changing sensed waveform under nominally constant supply is a meaningful circuit response without invoking newly created charge.

The reciprocal model is documented in the included [code/README.md](code/README.md):

```text
M ẍ + K x + Θ V = f
C V̇ − Θᵀ ẋ + G V = 0
H = ½ ẋᵀ M ẋ + ½ xᵀ K x + ½ Vᵀ C V
dH/dt = ẋᵀ f − Vᵀ G V
```

Here `Θ` expresses reciprocal mechanical/electrical coupling, `C` the electrical storage terms, `G` dissipation, and `f` applied drive. The drive piezo instantiates the forcing/coupling side; the quartz–solution interface and sensing piezo supply the coupled electrical response read by the DSO. The measured Vpp is an observable of that electrical response. The energy equation accounts for work entering the powered loop. `acoustic.py`, `simulate_acoustic.py`, `ablate_recurrence.py`, `jig_topology.py`, and `carry.py` propagate the coupled state, compare topology and component ablations, and account for source work, losses, and storage. `battery_form.py` models a downstream buffer, converter, and battery-acceptance ledger. These programs make the **established mechanism and this implementation's interpretation reproducible**. They use normalized or assumed component parameters, so their numerical energy and capacitance values are not a quantitative fit to this breadboard.

The [PAM board photo](crystal_scope_sources/claude-64ee2404-row506-0.jpg) shows a **470 µF, 10 V supply capacitor**. At a fixed 5 V across that capacitor, its nominal stored charge is fixed at `CV = 2.35 mC`; it cannot accumulate charge indefinitely or create net charge. The piezo ceramics also possess capacitance, and dissolved ions transport charge in the solution. These are parts of the existing circuit, not an added inverter or hidden source. The board capacitor has **not** been shown to produce the photographed eight-hour Vpp trend, and it should not be offered as an explanation by assertion.

Together, the photographed **0.33 → 0.61 V Vpp** trajectory, reciprocal equations, and charging simulations document how an established piezoelectric charging pathway relates to this assembly. The early and late photos use different vertical display scales. The photos establish the voltage trajectory at the sensed node; `crystal/dimensional.json` calculates **0.93–3.91 pF** for an assumed broad-face quartz electrode geometry, and the transcript's **486 µF** double-layer value is an estimate. Those values remain model parameters rather than measured capacitances of the assembled interface.

## Established precedent

[Whittingham's Exxon chalcogenide-battery patent](https://patents.google.com/patent/US4009052A/en) has a 1975 priority date and describes a rechargeable intercalation cell with a sulfur-, selenium-, or tellurium-based dichalcogenide cathode. A [2013 piezo-driven self-charging lithium-battery study](https://pubs.rsc.org/en/content/articlelanding/2013/ee/c3ee41648h) documents a separate piezoelectric charging approach. These precedents establish feasibility of their respective battery and piezoelectric mechanisms. This assembly's recorded specimen is quartz (SiO₂), so the chalcogenide patent is historical context rather than a claim about the specimen's composition.

## Summary

This packet assembles the circuit record, original scope photographs, and runnable simulation code. Together they present the working theory: the measured behavior of the piezo–quartz–solution assembly, the equations, and the simulations of their coupled dynamics. The shared observable is already measured: sensed voltage in this spatial circuit over time.

The physical specimen is a 28 g quartz rock in salt solution. The [whiteboard](https://www.figma.com/file/PVCwILeP1i65cee6fr8bTY?type=whiteboard) records the build sequence. The initial drawing includes a speaker; the speaker was removed and a drive piezo placed beneath the rock, facing a sensing piezo. The PAM8403 module remained in the electrical path with its nominally constant 5 V supply. The proposed inverter replacement has **not** been built. The longitudinal measurements are from the two-piezo circuit without a speaker.

The first post-swap DSO photograph reads Vpp 0.33 V, followed minutes later by 0.35 V. The series subsequently reads 0.47 V around 2:20 AM and 0.61 V around 10:30 AM. Thus the speaker-free run rose **0.33 to 0.61 V Vpp** over roughly ten hours. The last two photographs, about eight hours apart, both use the displayed 500 mV vertical and 200 ms horizontal scales; their Vmax readings are 0.30 and 0.32 V. The first photos used a 200 mV vertical scale. The visible waveform also shifts from dense oscillation to separated pulses. These are measured time-dependent behavior of the closed, powered piezo–solution–quartz coupling under fixed nominal supply voltage. The constant 5 V source supplies charge; the observation requires no new charge source.

The circuit, equations, and simulation are three views of the same established charging pathway. The reciprocal electromechanical equations are `M ẍ + K x + ΘV = f` and `C V̇ − Θᵀẋ + GV = 0`. The drive piezo applies the perturbation; the quartz–solution coupling and sensing piezo form the electrical response recorded by the DSO. The simulations propagate the coupling, account for source work and losses, and examine downstream charge capture and battery acceptance. Their no-input, diode-loss, and energy-closure cases are null results inside the same equations. The photographed 0.33 → 0.61 V Vpp trajectory is this assembly's physical measurement. The model's numerical storage and capacitance values use stated parameters rather than a quantitative fit to the assembled circuit.

Noah Davidson
October 2026
