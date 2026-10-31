"""Measured single-crystal surrogate composed with the owner's stone geometry.

Material matrices are from Xie, Bai & Li's PE-EMIS measurements on one
24.03 g alpha-quartz rectangular parallelepiped.  Their sandwich-RUS values
provide a measured clamp-perturbed comparison, not an assumed multiplier.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from math import exp, pi, sqrt

from native import matrix as nm
from quartz_tensor_orientation import rotation_z_y_z


@dataclass(frozen=True)
class MeasuredQuartz:
    name: str
    c11: float
    c12: float
    c13: float
    c14: float
    c33: float
    c44: float
    e11: float
    e14: float
    epsilon11_relative: float = 4.424
    epsilon33_relative: float = 4.632


PE_EMIS_FREE = MeasuredQuartz("PE_EMIS_free", 86.72, 6.802, 11.81,
                              -18.10, 105.22, 58.22, 0.153, -0.040)
RUS_CLAMPED = MeasuredQuartz("sandwich_RUS_clamped", 86.79, 6.986, 11.75,
                             -18.04, 105.49, 58.32, 0.173, -0.070)


@dataclass(frozen=True)
class SurrogateRun:
    length: float = 1.5 * 0.0254
    width: float = 1.25 * 0.0254
    thickness: float = 0.5 * 0.0254
    mass: float = 0.028
    force: float = 100.0
    mechanical_q: float = 1.0 / 4.7e-4
    capture_efficiency: float = 0.90
    cycles: int = 1000

    @property
    def volume(self):
        return self.length * self.width * self.thickness


def _material_matrices(m):
    c66 = (m.c11 - m.c12) / 2.0
    # IEEE contracted form, coefficients converted from GPa to Pa.
    c = [[m.c11, m.c12, m.c13, m.c14, 0, 0],
         [m.c12, m.c11, m.c13, -m.c14, 0, 0],
         [m.c13, m.c13, m.c33, 0, 0, 0],
         [m.c14, -m.c14, 0, m.c44, 0, 0],
         [0, 0, 0, 0, m.c44, m.c14],
         [0, 0, 0, 0, m.c14, c66]]
    c = [[value * 1e9 for value in row] for row in c]
    e = [[m.e11, -m.e11, 0, m.e14, 0, 0],
         [0, 0, 0, 0, -m.e14, -2*m.e11],
         [0, 0, 0, 0, 0, 0]]
    eps0 = 8.8541878128e-12
    epsilon = nm.diagonal((m.epsilon11_relative*eps0,
                           m.epsilon11_relative*eps0,
                           m.epsilon33_relative*eps0))
    return c, e, epsilon


def measured_event(force, rotation, material=PE_EMIS_FREE,
                   run=SurrogateRun()):
    c, e, epsilon = _material_matrices(material)
    area = run.length * run.width
    stress_lab = [[0, 0, 0], [0, 0, 0], [0, 0, force/area]]
    rt = nm.transpose(rotation)
    stress = nm.multiply(nm.multiply(rt, stress_lab), rotation)
    t = [stress[0][0], stress[1][1], stress[2][2],
         stress[1][2], stress[0][2], stress[0][1]]
    strain = [row[0] for row in nm.solve(c, [[value] for value in t])]
    d_crystal = nm.matvec(e, strain)
    field_crystal = [row[0] for row in
                     nm.solve(epsilon, [[value] for value in d_crystal])]
    mechanical = 0.5 * run.volume * nm.dot(t, strain)
    electrical = 0.5 * run.volume * nm.dot(d_crystal, field_crystal)
    d_lab = nm.matvec(rotation, d_crystal)
    field_lab = nm.matvec(rotation, field_crystal)
    dims = (run.length, run.width, run.thickness)
    areas = (run.width*run.thickness, run.length*run.thickness,
             run.length*run.width)
    return {
        "mechanical_energy_joule": mechanical,
        "open_circuit_electrical_joule": electrical,
        "coupling_fraction": electrical/mechanical if mechanical else 0.0,
        "face_voltage_volt": [field_lab[i]*dims[i] for i in range(3)],
        "face_charge_coulomb": [d_lab[i]*areas[i] for i in range(3)],
    }


def recur_measured_orientation(rotation, material=PE_EMIS_FREE,
                               run=SurrogateRun()):
    unit = measured_event(1.0, rotation, material, run)
    mechanical = unit["mechanical_energy_joule"] * run.force**2
    initial = mechanical
    held = circuit_loss = q_loss = 0.0
    retention = exp(-2*pi/run.mechanical_q)
    trace = []
    for cycle in range(1, run.cycles+1):
        amplitude = sqrt(mechanical/unit["mechanical_energy_joule"])
        available_electrical = min(
            mechanical,
            unit["open_circuit_electrical_joule"] * amplitude**2)
        stored = run.capture_efficiency * available_electrical
        held += stored
        circuit_loss += available_electrical - stored
        after_capture = mechanical - available_electrical
        next_mechanical = retention * after_capture
        q_loss += after_capture - next_mechanical
        if cycle <= 5 or cycle in (run.cycles//2, run.cycles):
            trace.append({"cycle": cycle,
                          "dynamic_force_amplitude_newton": amplitude,
                          "contact_force_max_newton": run.force+amplitude,
                          "mechanical_joule": mechanical,
                          "stored_joule": stored})
        mechanical = next_mechanical
    return {
        "material": asdict(material), "run": asdict(run),
        "one_newton_event": unit, "initial_mechanical_joule": initial,
        "trace": trace,
        "energy": {"held_joule": held, "final_mechanical_joule": mechanical,
                   "circuit_loss_joule": circuit_loss, "q_loss_joule": q_loss,
                   "closure_residual_joule":
                       held+mechanical+circuit_loss+q_loss-initial},
    }
