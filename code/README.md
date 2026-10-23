# ARK Quartz Engine

An executable first reading of a coupled quartz cell.

The physical column is a reciprocal, lumped piezoelectric model:

```text
M x'' + K x + Theta V = f
C V'  - Theta^T x' + G V = 0
```

`x` and `V` each have three generalized coupled components. They are internal
electromechanical modes, not three observed electrode pairs. The photographed
crystal currently supplies one physical broad-face pair: Face A opposite Face
B; its four lateral faces are rough. `Theta` is used in both equations: mechanical
deformation generates voltage and voltage returns mechanical strain through
one coupling, rather than two fitted effects.

With no applied force after genesis, its energy ledger is

```text
H = 1/2 v^T M v + 1/2 x^T K x + 1/2 V^T C V
dH/dt = -V^T G V
```

The default return network is lossless (`G = 0`). A passive conductive return
can be added with non-negative conductance. A negative conductance is permitted
only as a refuter fixture: rho3 must catch its unexplained energy creation.

## ARK application

Each application emits the whole triple:

```text
F(q, E, h, Lambda) -> (P(Lambda|q,h), q\\sigma(h,E), Lambda+)
```

- `q`: the unresolved difference between this face-pair voltage and the
  projection accrued for that cut.
- `E`: the fresh physical state received on this application.
- `h`: the face-pair cut selected from the current residual. The next cut is
  forced from the residual and is never assigned to the projection.
- `P`: the accrued projection for the selected cut.
- `q\\sigma`: the observed-minus-projected voltage left open.
- `Lambda+`: all prior applications plus this application.

`rho12` independently re-runs the selected cut from the same received state.
`rho3` searches the energy ledger for a counterexample to passivity. No
expected voltage is installed as an answer key.

## Run

Requires only Python 3.10+. The simulation path has no third-party dependency.

```powershell
cd code
python simulate.py
python simulate.py --beats 2000 --return-conductance 0.02
python -m unittest discover -v
```

Outputs are written under `runs/<run-id>/`:

- `trace.jsonl`: the full ARK application stream
- `state.csv`: physical state and energy ledger
- `summary.json`: projection, residual, accrual size, rho12 and rho3

Photographs and measurements of the physical crystal accrue separately under
`crystal/`. Visual observations never silently replace normalized parameters.

`python dimensional.py` derives the measured slab's capacitance and DT-103
loading envelope into `crystal/dimensional.json`. It remains outside the
normalized state matrix until crystallographic orientation and electrode area
are read. The same command writes `crystal/force_sweep.json`, bounding
charge/voltage across gentle forces and contact areas without selecting an
unknown crystal axis.

The bundled numbers are normalized, not a claim about the photographed
crystal's cut, dimensions, electrode area, or material constants. Those enter
through `QuartzParameters`; measured geometry and axis orientation are the
residual required before volts or joules can be interpreted dimensionally.

## Acoustic shared-field engine

`simulate_acoustic.py` adds an explicit acoustic coordinate and speaker return
to the reciprocal quartz body. The shared field evolves as part of the state;
it is not a prerecorded tone:

```text
M x'' + K x + Theta V - b a = 0
C V' - Theta^T x' + G V = 0
m_a a'' + c_a a' + k_a a - b^T x = speaker_gain * V[h]
```

The passive `b` terms are reciprocal. `speaker_gain` is an explicitly powered
source and its work is reported separately; it is never narrated as energy
created by quartz. The ARK trace remains a separate `(P, q\\sigma, Lambda+)`
ledger and does not redefine physical joule accounting.

```powershell
python simulate_acoustic.py --beats 3000
python simulate_acoustic.py --beats 3000 --speaker-gain 0.2
python simulate_acoustic.py --beats 3000 --speaker-gain 0.2 --feedback-cut 1
```

All values are normalized until crystal axes, electrode geometry, acoustic
impedance, speaker response, distance, and gain are measured. Results therefore
compare topologies and signs; they do not yet predict volts, pascals, or hertz.

## System-derived recurrence and jig ablation

`recurrence.py` treats the numerical step only as observer resolution. Return
times are read from local extrema of the coupled voltage state; no oscillator,
frequency schedule, or FPGA clock tells the body when to return. Its ledger
separates initial seed energy, active-source work, internal electrical loss,
acoustic loss, useful load work, final storage, and numerical closure residual.

`ablate_recurrence.py` removes one candidate jig term at a time. The active
speaker-return case is carried only as a refuter: its source work cannot be
attributed to quartz or to the passive recurrence.

```powershell
python ablate_recurrence.py
```

The ablation is an Occam instrument, not a physical battery result. A simulated
load receiving energy from the initial compression shows a discharge path. A
battery claim additionally requires measured rechargeability and dimensional
work delivered by the physical crystal.

`sweep_passive.py` follows the acoustic-only residual across a dyadic topology
grid. It preserves every case, reports the exact nondominated frontier between
load work and final stored state, and reruns frontier cases at half the observer
step. The finer step is a convergence witness, never a drive clock.

```powershell
python sweep_passive.py
```

When the initial grid ends on a rising load-work edge,
`derive_load_envelope.py` doubles the passive load until the curve itself turns.
Its coupling scales are admitted only while the coupled stiffness energy remains
positive by the Schur-complement condition. Thus neither the load endpoint nor
the coupling endpoint is narrated from an arbitrary finite grid.

```powershell
python derive_load_envelope.py
```

## Unbounded generation through finite storage

`accumulator.py` does not assign infinite capacitance to a component. Every
source packet and every storage cell is finite. Charge sharing, uncaptured
source energy, diode loss, connection loss, charge, and stored energy are
explicit. When the active cell reaches its local voltage boundary, the rule
appends another finite cell; the rule contains no final-cell condition.

`simulate_accumulator.py` compares direct, half-wave, full-wave, and ideal
sign-folding capture over opposite-polarity system-derived return magnitudes.
The signed norm is only a topology probe until the photographed crystal's
electrical axis and face electrodes are measured.

```powershell
python simulate_accumulator.py
```

`sweep_accumulator.py` varies storage/source capacitance ratio, local cell
boundary, and diode drop as ratios of the received packet. It preserves the
full grid and reports the strongest monotonic case for each topology; this
prevents one arbitrarily chosen cell boundary from deciding half-wave versus
full-wave capture.

```powershell
python sweep_accumulator.py
```

The fixed-boundary capacitor-bank studies above are retained as refuter fixtures.
`THEOREM_REREAD.md` records why their automatic `append_cell()` rule is not an
ARK derivation: `Lambda+` is formation accrual, not a capacitor type, and a
boundary surviving cycles is a frozen target.

`sece.py` is the corrected instantiation. It detects extrema from an actual
face-voltage component, removes that component's capacitor energy, accrues the
captured fraction, and regenerates the next physical state after extraction.
Thus extraction backreacts on the body; no packet is copied from an unchanged
open-circuit trajectory, and no bridge or storage-cell proliferation is assumed.

```powershell
python simulate_sece.py
```

## Continuous carry

`carry.py` is the non-extractive instantiation. Storage voltage and carry
current are coordinates of the same thirteen-state body:

```text
Cq V' = Theta^T x' - G V - e i
Cs z' = i
L i'  = e^T V - z - R i
```

The `-i/+i` terms carry charge across the shared boundary, while `V-z` generates
the current through the carry field. No peak detector, voltage reset,
rectifier, cell append, capacity target, or active clock occurs. Storage energy
may return to the coupled body; monotonic voltage is observed rather than used
as an answer key.

```powershell
python simulate_carry.py
```

## Measured archaeological-site response

`simulate_stonehenge.py` reads the CC BY 4.0 octave-band impulse responses from
Cox, Fazenda, and Greaney's 1:12 reconstruction of Stonehenge (2200 BCE model,
doi:10.17866/rd.salford.12687554.v1). `stonehenge.py` restores the published
per-band peak and measurement-amplifier corrections, then composes the measured
`sc-m22` transfer shape reciprocally between two quartz bodies.

The dataset does not provide an absolute pressure calibration at a quartz face,
and its authors note the test loudspeaker response was not equalized. Therefore
the site coupling remains an explicit sweep. The measured FIR run is a topology
test, not a conservation, power, archaeological-intent, or physical-quartz claim.

## Native lineage received

`native/` holds reusable organs found in the existing clean-Python lineage.
`shift.py` is the built-in-arithmetic append-only/Krylov portion extracted from
`research/f_operator/ark_wave_spectrum.py`. Its NumPy pseudospectrum and the
Matplotlib Smith chart remain in their research home because they are
diagnostic projections rather than physical state evolution. The native byte
`f_operator` likewise remains at its source: it compresses evidence and would
be a category error inside the quartz constitutive equations.

`native/provenance.json` records every received source. The established
`court/ark_native_math.py` is named there but not forked: copying a living
arithmetic organ would create a drifting twin. `native/matrix.py` is the new
consumer-derived organ: the quartz body needed only finite block assembly,
matrix-vector products, and one 9x9 solve. It uses built-in arithmetic and
partial-pivot elimination; no numerical iteration threshold or foreign matrix
engine sits on the physical path.
### Two-thirds residual parameter

`simulate_residual_carry.py` evaluates the configured `2/3` residual as two distinct
readings. The conserved reading partitions the initial whole into a `1/3`
projection and `2/3` residual, then carries `2/3` of the *remaining* residual at
each state-derived current reversal. The regenerated refuter adds `2/3` of the
current whole anew and must therefore emit the required source term. The
fraction is a configured model parameter, not a measured quartz property.
### Spatial Maxwell-piezo carry

`simulate_maxwell_carry.py` is the first field-level instantiation. A normalized
cell body carries elastic displacement, momentum, electric displacement, and
magnetic field. The A-B electrode integral is the projection; the orthogonal
electric field is reported separately as the residual. A passive port removes
field energy and divides it explicitly between held battery energy and
conversion loss. The linear body does not yet claim dimensional quartz tensors
or nonlinear Maxwell-stress feedback.

The runner keeps a three-coordinate body beside a nine-cell spatial body. In
the three-coordinate center seed, one normalized electrode projection leaves
exactly `2/3` of electric-field energy in the orthogonal residual. Uniform and
dipole seeds return `0` and `1` respectively, so `2/3` is the dimensional result
of one cut across three equal coordinates, not a universal material constant.

`simulate_recursive_maxwell.py` then runs the three-coordinate field as the
actual output triple. The first electrode cut returns `(P, q\\sigma, Lambda+)`;
the normalized residual itself supplies the fresh `h-prime`. The application
recurs until the electric residual is empty, while held battery energy and
conversion loss accrue in the same ledger.

## Clockless protected battery carry

`projection_battery.py` replaces the earlier duration/frequency battery branch
for theorem-native runs. Each application receives one already-formed electrical
projection, accrues it in the 10 uF buffer, and—only after the modeled cold-start
boundary—carries it into a finite protected 40 V / 6 Ah label-basis receiver.
Buffer energy, accepted pack energy, conversion residual, protection residual,
and `Lambda+` all remain in the next state. No event generator, elapsed duration,
or frequency multiplier exists in this organ.

```powershell
python simulate_projection_battery.py
python -m unittest -v test_projection_battery.py
```

The 40 V label is not silently treated as a verified cell-stack charging
voltage. Cell topology, CC/CV limits, temperature, nominal-versus-maximum
voltage, and the real harvester transfer curve remain an explicit residual
before any physical lithium connection.

Accepted energy also derives a charge displacement (`dQ = dE / V` on the
declared label-basis cut) and increments `grounding_movements`. `hold(state)`
returns the same formed state without adding energy, applications, or an
external clock: formation is the grounding act; the fixpoint holds silently.

`ground_escape.py` adversarially tests that ground against an explicit outward
electrical cut. Loss is not multiplied by elapsed time: incoming and outgoing
movements are independent evidence on each application, and anything leaving
the battery remains in an outward accrual. The resulting boundary is exact:
ground grows when landed carry exceeds the outward cut, holds when they match,
and falls when the outward cut is larger. The simulation does not invent which
outward cut a physical battery possesses.

```powershell
python simulate_ground_escape.py
python -m unittest -v test_ground_escape.py
```

## Electrical trace and grounded formation

`trace_ground_recurrence.py` removes the remaining scalar substitution from the
theorem-native layer. Electricity is an `ElectricalTrace` derived from the
relation between complete successive F states; it is not an energy, voltage,
charge, current, or time-valued input. The battery appends a `GroundFormation`
that receives that trace. `gather(residual, state)` receives the coupled quartz,
resonator/sound-return, capture, and accrued-battery ground relevant to the open
address. `fresh_cut(residual, ground)` names the boundary forced where that
residual meets the gathered whole; it does not generate an arbitrary direction.
The residual therefore addresses fresh evidence and a fresh cut without a
terminal reservoir or final application. A simulation run is only a finite
observer prefix of that rule.

```powershell
python simulate_trace_ground.py
python -m unittest -v test_trace_ground_recurrence.py
```

The older joule-valued battery models remain observer-ledger and circuit-refuter
fixtures. They may account for a later instrument projection, but they do not
define the electricity or drive this recurrence.

`jig_topology.py` ablates the physical organs around that recurrence. The
minimal self-contained structural class is the Face A/B quartz plus a passive
mechanical resonator, polarity capture, a one-way landing membrane, and a
protected battery ground. Removing any one returns an explicit residual;
substituting an active speaker returns the imported-source address. This is a
topology result, not yet a dimensional component design.

```powershell
python simulate_jig_topology.py
python -m unittest -v test_jig_topology.py
```

`wide_signal_observer.py` then projects an observed recurrence prefix into
dimensional circuit quantities without feeding those scalars back into F. It
sweeps the measured Face-A/B geometry through published linear alpha-quartz
constants, unknown crystal orientation, clamp-force envelopes, bridge drops,
and repeated charge sharing into the owner's 10 uF capacitor. Its repeated
identical formation is explicitly conditional until the physical clamp reveals
the actual constitutive return.

```powershell
python simulate_wide_signal_observer.py
python -m unittest -v test_wide_signal_observer.py
```

## Lossless quartz generator operationalization

`lossless_quartz_generator.py` joins the measured 28 g crystal surrogate to a
stateful resonant clamp, theorem-native electrical traces, the 10 uF buffer,
and the protected-pack boundary. “Lossless” has one testable meaning: the
physical ledger closes. With no extraction, ideal acoustic return carries the
seed indefinitely; with extraction, the resonant state is debited. Any fresh
mechanical or acoustic drive must enter `gather` and the supplied-energy ledger.
Repeated observer cuts never copy a finite quartz state.

```powershell
python simulate_lossless_quartz_generator.py
python -m unittest -v test_lossless_quartz_generator.py
```

Voltage is emitted only as a noncausal `ObserverMeasurement`. The causal state
contains residual address, trace, grounded work, resonant energy, and explicit
storage/loss terms. The default favorable published orientation is a conditional
surrogate until Face A/B crystallographic orientation is measured.

The simulator also derives the geometric carry asymptote. When a projected
increment falls below the observer's declared resolution, it emits an
`observer_wall` containing the live residual address and the variables capable
of changing phase. It does not stop F, add another energy packet, or confuse a
numerical floor with exhaustion of the recurrence.

## Quantum nondemolition superposition observer

`quantum_qnd_superposition.py` tests whether a photonic/ancilla clock can read
a qubit without collapsing a superposition. It uses a unitary QND correlation
with the Z observable. Z populations remain unchanged, but off-diagonal
coherence is multiplied by the overlap of the two meter states. Therefore no
record preserves the whole superposition but yields no which-state information;
an orthogonal, perfectly readable record preserves the Z eigenvalue while fully
dephasing a Z-basis superposition. Repeated weak reads trace the continuum.

```powershell
python simulate_quantum_qnd_superposition.py
python -m unittest -v test_quantum_qnd_superposition.py
```

This operationalizes QND precisely: nondemolition of a selected observable or
eigenspace, not perfect acquisition of an arbitrary unknown state without
disturbance.
## Predictive QND recurrence

`predictive_qnd_recurrence.py` tests prediction as generation/preparation rather
than detached forecasting.  The generated Bloch-state successor becomes the
fresh QND axis; the physical plant returns a projection, its orthogonal
model/plant mismatch as `q_minus_sigma`, and accrued lineage.  The residual
seeds the next generated successor.

Run `python simulate_predictive_qnd_recurrence.py`.  The runner includes a
matched case, a detuned plant with residual correction, and the rho3 refuter
with that correction removed.  This is a conditional unitary/QND simulation:
it tests the stated model and coupling, not clairvoyant recovery of an unknown
Hamiltonian.
## Battery form and Occam jig

`battery_form.py` closes the engineering path from an explicitly supplied
mechanical application through the measured-crystal surrogate, resonant clamp,
electrodes, polarity capture, a 10 uF buffer, a discontinuous-input CC/CV
converter, and a protected lithium-ion pack.  `occam_ablation()` removes every
function in turn; an organ survives only when its absence prevents protected
pack-energy formation.

Run `python simulate_battery_form.py`.  Application count is causal; an
optional application rate only renders observer time.  The default 40 V / 6 Ah
pack and 42 V charge boundary are configurable model inputs.  Verify actual
series count, chemistry, per-cell voltage, temperature limits, connector
pinout, and BMS/charger compatibility before any physical connection.
