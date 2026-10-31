# Quartz–Piezo Circuit

A speaker-free quartz–piezo circuit whose sensed voltage rises from 0.33 to 0.61 Vpp over ten hours under a constant 5 V supply. Original oscilloscope photographs, reciprocal electromechanical equations, and runnable simulations.

**Noah Davidson, October 2026**

## The experiment

A 28 g quartz rock sits in salt solution between two piezo elements — one drives, one senses. The PAM8403 module supplies a nominal 5 V. No speaker, no audio, no inverter. The DSO reads the sensing piezo.

Over roughly ten hours, the photographed Vpp rises:

| Time | Vpp | Vmax |
|------|-----|------|
| 12:48 AM | 0.33 V | 0.16 V |
| 12:50 AM | 0.35 V | 0.18 V |
| 2:20 AM | 0.47 V | 0.30 V |
| 10:30 AM | 0.61 V | 0.32 V |

The original scope photographs are in `crystal_scope_sources/`. SHA-256 hashes and display-scale notes are in `EVIDENCE.md`.

## The equations

Standard reciprocal piezoelectric coupling:

```
M x'' + K x + Theta V = f
C V'  - Theta^T x' + G V = 0
H = 1/2 x'^T M x' + 1/2 x^T K x + 1/2 V^T C V
dH/dt = x'^T f - V^T G V
```

The energy ledger closes. No hidden source. The drive piezo applies the perturbation; quartz–solution coupling and sensing piezo form the response. `EVIDENCE.md` has the full physics statement.

## Run

Python 3.10+. No third-party packages.

```
cd code
python simulate.py --beats 100
python simulate_battery_form.py
python simulate_carry.py
python simulate_acoustic.py --beats 300 --speaker-gain 0
python ablate_recurrence.py
```

Results go to `code/runs/`. See `RUN_ME.md` for details.

## What's here

- `EVIDENCE.md` — full evidence document: voltage series, wiring chronology, equations, analysis
- `crystal_scope_sources/` — original oscilloscope photographs (JPEGs, SHA-256 verified)
- `schematics/` — circuit SVGs: speaker-free reconstruction, v2, complete, self-sustaining proposal
- `code/` — reciprocal equations, simulations, topology ablation, battery-form model
- `code/crystal/` — crystal geometry, observations, dimensional analysis
- `simulations/` — saved simulation outputs
- `data/` — build chronology excerpts, scope readings

## License

CC0 1.0 Universal — public domain dedication.
