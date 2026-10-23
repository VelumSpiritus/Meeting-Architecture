"""Rotate the published alpha-quartz tensors through the owner's stone geometry."""

from __future__ import annotations

from dataclasses import dataclass
from math import acos, cos, pi, sin, sqrt

from dual_storage_jig import DualJigParameters, run_battery_branch, run_measure_branch
from native import matrix as nm


@dataclass(frozen=True)
class QuartzTensorParameters:
    length: float = 1.5 * 0.0254
    width: float = 1.25 * 0.0254
    thickness: float = 0.5 * 0.0254
    d11: float = 2.31e-12
    d14: float = 0.727e-12
    epsilon11: float = 39.97e-12
    epsilon33: float = 41.03e-12

    @property
    def volume(self):
        return self.length * self.width * self.thickness


def rotation_z_y_z(alpha, beta, gamma):
    ca, sa, cb, sb, cg, sg = (cos(alpha), sin(alpha), cos(beta), sin(beta),
                               cos(gamma), sin(gamma))
    rz1 = [[ca, -sa, 0.0], [sa, ca, 0.0], [0.0, 0.0, 1.0]]
    ry = [[cb, 0.0, sb], [0.0, 1.0, 0.0], [-sb, 0.0, cb]]
    rz2 = [[cg, -sg, 0.0], [sg, cg, 0.0], [0.0, 0.0, 1.0]]
    return nm.multiply(nm.multiply(rz1, ry), rz2)


def tensor_event(force, rotation, p=QuartzTensorParameters()):
    """Uniaxial lab-z force; rotation maps crystal vectors into lab vectors."""
    if force < 0.0:
        raise ValueError("force must be non-negative")
    area_z = p.length * p.width
    stress_lab = [[0.0, 0.0, 0.0], [0.0, 0.0, 0.0],
                  [0.0, 0.0, force / area_z]]
    rt = nm.transpose(rotation)
    stress = nm.multiply(nm.multiply(rt, stress_lab), rotation)
    voigt = [stress[0][0], stress[1][1], stress[2][2],
             stress[1][2], stress[0][2], stress[0][1]]
    d = [[p.d11, -p.d11, 0.0, p.d14, 0.0, 0.0],
         [0.0, 0.0, 0.0, 0.0, -p.d14, -2.0 * p.d11],
         [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]]
    displacement_crystal = nm.matvec(d, voigt)
    displacement_lab = nm.matvec(rotation, displacement_crystal)
    epsilon_crystal = nm.diagonal((p.epsilon11, p.epsilon11, p.epsilon33))
    epsilon_lab = nm.multiply(nm.multiply(rotation, epsilon_crystal), rt)
    field_column = nm.solve(epsilon_lab, [[value] for value in displacement_lab])
    field_lab = [row[0] for row in field_column]
    event_energy = 0.5 * p.volume * nm.dot(displacement_lab, field_lab)

    dimensions = (p.length, p.width, p.thickness)
    face_areas = (p.width * p.thickness, p.length * p.thickness,
                  p.length * p.width)
    charges = [displacement_lab[i] * face_areas[i] for i in range(3)]
    # Open-circuit component voltages from E_i times separation. Coupled
    # off-diagonal epsilon is already included through E = epsilon^-1 D.
    voltages = [field_lab[i] * dimensions[i] for i in range(3)]
    return {"force_newton": force, "D_lab": displacement_lab,
            "E_lab": field_lab, "face_charge": charges,
            "face_voltage": voltages, "event_energy": event_energy}


def orientation_sweep(force=10.0, step_degrees=15,
                      p=QuartzTensorParameters(), jig=DualJigParameters()):
    if step_degrees <= 0 or 180 % step_degrees:
        raise ValueError("step_degrees must be a positive divisor of 180")
    events = []
    polar_count = 180 // step_degrees
    for a_deg in range(0, 360, step_degrees):
        for polar_index in range(polar_count):
            # Haar-uniform polar sampling uses uniform cos(beta), with
            # midpoints avoiding duplicated Euler poles.
            beta = acos(-1.0 + 2.0 * (polar_index + 0.5) / polar_count)
            for g_deg in range(0, 360, step_degrees):
                rotation = rotation_z_y_z(a_deg*pi/180, beta, g_deg*pi/180)
                event = tensor_event(force, rotation, p)
                event["euler_degrees"] = [a_deg, beta*180/pi, g_deg]
                events.append(event)
    energies = sorted(event["event_energy"] for event in events)
    max_face_voltages = sorted(max(abs(value) for value in event["face_voltage"])
                               for event in events)
    nonzero = [value for value in energies if value > 1e-35]
    def quantile(values, fraction):
        return values[round(fraction * (len(values) - 1))]
    representative = {
        "minimum": energies[0], "p05": quantile(energies, 0.05),
        "median": quantile(energies, 0.5), "p95": quantile(energies, 0.95),
        "maximum": energies[-1], "minimum_nonzero": nonzero[0] if nonzero else 0.0,
    }
    cases = {name: {"event_energy": value,
                    "measure": run_measure_branch(value, jig),
                    "battery": run_battery_branch(value, jig)}
             for name, value in representative.items()}
    return {"parameters": p.__dict__, "force_newton": force,
            "orientation_count": len(events), "energy_quantiles": representative,
            "max_face_voltage_quantiles": {
                "p05": quantile(max_face_voltages, 0.05),
                "median": quantile(max_face_voltages, 0.5),
                "p95": quantile(max_face_voltages, 0.95),
                "maximum": max_face_voltages[-1]},
            "cases": cases,
            "q_minus_sigma": (
                "The tensor is complete for linear direct piezoelectricity; stress nonuniformity, "
                "twins/fractures, contact mechanics, modal resonance, damping, and circuit loading "
                "remain properties of this stone and jig."
            )}
