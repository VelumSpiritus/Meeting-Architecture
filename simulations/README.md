# Circuit simulation trail

This folder preserves the saved outputs from the Quartz Engine runs. The runnable source is in `../code/`; use Python 3.10+ from that directory. The programs use the standard library.

| Model | Run from `code/` | What it tests |
|---|---|---|
| Reciprocal piezoelectric model | `python simulate.py --beats 100` | Coupled mechanical/electrical state and energy balance. |
| Passive charging jig | `python simulate_passive_jig_circuit.py` | Finite piezo capacitances transfer charge to a reservoir across ideal, low-drop, and Schottky-like diode controls; mechanical input and losses close the energy ledger. |
| Dual storage | `python simulate_dual_storage_jig.py` | Separates a high-impedance measurement branch from an energy-accepting battery branch. |
| Joint jig and battery sweep | `python simulate_joint_jig_battery_sweep.py` | Sweeps the assumed coupling from jig output to battery acceptance. |
| Full-pack accumulation | `python simulate_full_pack_accumulate_charge.py` | Parameter sweep for charge acceptance under an assumed external mechanical source. |
| Measured-crystal surrogate | `python simulate_measured_crystal_surrogate.py` | Carries literature crystal measurements into a separately stated surrogate geometry. |
| Battery-form ablation | `python simulate_battery_form.py` | Removes modeled components in turn and checks the energy-acceptance boundary. |

Controls can be rerun with `python -m unittest -v test_passive_jig_circuit.py test_full_pack_accumulate_charge.py test_joint_jig_battery_sweep.py`. Saved `summary.json` files below are the original run outputs, copied without numerical changes. Their run names preserve dates.

These simulations establish the behavior and energy accounting of the specified equations and parameter sets. The no-input, diode-loss, and energy-closure controls are null cases within those equations. The saved runs predate the photographed speaker-free build and use stated normalized or literature-derived parameters. The photographs document the actual 0.33–0.61 Vpp sensed-voltage series; the simulations give the working theory's mechanism and controls in runnable form.

## Saved outputs

- [passive-jig-20260813T224207.225152Z/summary.json](results/passive-jig-20260813T224207.225152Z/summary.json) — passive-jig
- [dual-storage-20260813T231032.428359Z/summary.json](results/dual-storage-20260813T231032.428359Z/summary.json) — dual-storage
- [full-pack-20260814T042327.953421Z/summary.json](results/full-pack-20260814T042327.953421Z/summary.json) — full-pack
- [joint-jig-battery-20260814T045602.003237Z/summary.json](results/joint-jig-battery-20260814T045602.003237Z/summary.json) — joint-jig-battery
- [battery-form-20260814T192246.936550Z/summary.json](results/battery-form-20260814T192246.936550Z/summary.json) — battery-form
- [measured-surrogate-20260814T005632.062824Z/summary.json](results/measured-surrogate-20260814T005632.062824Z/summary.json) — measured-surrogate
