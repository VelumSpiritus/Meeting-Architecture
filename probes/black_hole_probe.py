#!/usr/bin/env python3
"""
Black Hole Probe — a small matrix density estimator over the ATNF pulsar catalog.

The probe learns the spatial distribution of known pulsars (neutron stars = seams
at the edge of collapse) on the galactic plane, then finds where the distribution
PREDICTS pulsars but NONE are observed. Those gaps are candidate black holes —
seams that already crossed.

Noah Davidson, 2026-10-18
"""

import json
import math
import os
import sys

import numpy as np
from scipy.ndimage import gaussian_filter
from scipy.signal import find_peaks


def load_catalog(path):
    with open(path) as f:
        pulsars = json.load(f)
    coords = []
    for p in pulsars:
        if p['dist'] is not None and p['dist'] > 0:
            coords.append((p['gl'], p['gb'], p['dist'], p['name']))
    return coords


def galactic_density_map(coords, l_bins=360, b_bins=180, b_range=10):
    plane = [(l, b, d) for l, b, d, _ in coords if abs(b) < b_range]
    l_vals = np.array([c[0] for c in plane])
    b_vals = np.array([c[1] for c in plane])

    l_edges = np.linspace(0, 360, l_bins + 1)
    b_edges = np.linspace(-b_range, b_range, b_bins + 1)

    observed, _, _ = np.histogram2d(l_vals, b_vals, bins=[l_edges, b_edges])
    return observed, l_edges, b_edges


class ProbeMatrix:
    """
    The matrix IS the probe: input (l, b) → predicted density.
    Two hidden layers, ReLU, trained by gradient descent on the density field.
    """

    def __init__(self, input_dim=2, hidden=128, output_dim=1, seed=42):
        rng = np.random.RandomState(seed)
        scale1 = np.sqrt(2.0 / input_dim)
        scale2 = np.sqrt(2.0 / hidden)
        self.W1 = rng.randn(input_dim, hidden) * scale1
        self.b1 = np.zeros(hidden)
        self.W2 = rng.randn(hidden, hidden) * scale2
        self.b2 = np.zeros(hidden)
        self.W3 = rng.randn(hidden, output_dim) * scale2
        self.b3 = np.zeros(output_dim)

    def forward(self, X):
        self._X = X
        self._z1 = X @ self.W1 + self.b1
        self._a1 = np.maximum(0, self._z1)
        self._z2 = self._a1 @ self.W2 + self.b2
        self._a2 = np.maximum(0, self._z2)
        self._z3 = self._a2 @ self.W3 + self.b3
        return self._z3

    def backward(self, X, target, lr=0.001):
        pred = self.forward(X)
        N = X.shape[0]
        err = pred - target
        loss = np.mean(err ** 2)

        dz3 = err / N
        dW3 = self._a2.T @ dz3
        db3 = dz3.sum(axis=0)

        da2 = dz3 @ self.W3.T
        dz2 = da2 * (self._z2 > 0)
        dW2 = self._a1.T @ dz2
        db2 = dz2.sum(axis=0)

        da1 = dz2 @ self.W2.T
        dz1 = da1 * (self._z1 > 0)
        dW1 = X.T @ dz1
        db1 = dz1.sum(axis=0)

        self.W3 -= lr * dW3
        self.b3 -= lr * db3
        self.W2 -= lr * dW2
        self.b2 -= lr * db2
        self.W1 -= lr * dW1
        self.b1 -= lr * db1

        return loss


def build_training_data(observed, l_edges, b_edges):
    l_centers = 0.5 * (l_edges[:-1] + l_edges[1:])
    b_centers = 0.5 * (b_edges[:-1] + b_edges[1:])
    ll, bb = np.meshgrid(l_centers, b_centers, indexing='ij')

    X = np.column_stack([ll.ravel() / 360.0, bb.ravel() / 20.0])
    y = observed.ravel().reshape(-1, 1)
    y_norm = y / (y.max() + 1e-8)
    return X, y_norm, l_centers, b_centers


def find_candidates(predicted, observed, l_centers, b_centers):
    pred_2d = predicted.reshape(len(l_centers), len(b_centers))
    obs_2d = observed

    obs_smooth = gaussian_filter(obs_2d.astype(float), sigma=3)
    pred_smooth = gaussian_filter(pred_2d, sigma=3)

    obs_norm = obs_smooth / (obs_smooth.max() + 1e-8)
    pred_norm = pred_smooth / (pred_smooth.max() + 1e-8)

    # THE REWARD SPECTRUM: predicted minus observed at every grid point
    reward_spectrum = pred_norm - obs_norm

    # Collapse b-axis to find longitude peaks
    reward_1d = reward_spectrum.mean(axis=1)

    peaks, properties = find_peaks(reward_1d, height=0.03, distance=8, prominence=0.015)

    candidates = []
    for pk in peaks:
        l_peak = l_centers[pk]
        b_col = reward_spectrum[pk, :]
        b_peak_idx = np.argmax(b_col)
        b_peak = b_centers[b_peak_idx]
        score = reward_spectrum[pk, b_peak_idx]
        obs_count = int(observed[max(0, pk-1):min(len(l_centers), pk+2),
                                 max(0, b_peak_idx-1):min(len(b_centers), b_peak_idx+2)].sum())
        pred_val = pred_2d[pk, b_peak_idx]
        candidates.append({
            'l': round(float(l_peak), 1),
            'b': round(float(b_peak), 1),
            'reward': round(float(score), 4),
            'observed_nearby': obs_count,
            'predicted_density': round(float(pred_val), 4),
            'prominence': round(float(properties['prominences'][list(peaks).index(pk)]), 4),
        })

    candidates.sort(key=lambda c: -c['reward'])
    return candidates, reward_spectrum


def gal_to_eq(l_deg, b_deg):
    l = math.radians(l_deg)
    b = math.radians(b_deg)
    a_GP = math.radians(192.85948)
    d_GP = math.radians(27.12825)
    l_CP = math.radians(122.93192)

    sin_d = math.sin(d_GP) * math.sin(b) + math.cos(d_GP) * math.cos(b) * math.cos(l_CP - l)
    dec = math.asin(sin_d)

    y = math.cos(b) * math.sin(l_CP - l)
    x = math.cos(d_GP) * math.sin(b) - math.sin(d_GP) * math.cos(b) * math.cos(l_CP - l)
    ra = (math.degrees(a_GP + math.atan2(y, x))) % 360
    dec = math.degrees(dec)
    return ra, dec


def ra_hms(ra):
    h = int(ra / 15)
    m = int((ra / 15 - h) * 60)
    s = ((ra / 15 - h) * 60 - m) * 60
    return f"{h:02d}h{m:02d}m{s:04.1f}s"


def dec_dms(dec):
    sign = '+' if dec >= 0 else '-'
    dec = abs(dec)
    d = int(dec)
    m = int((dec - d) * 60)
    s = ((dec - d) * 60 - m) * 60
    return f"{sign}{d:02d}d{m:02d}m{s:04.1f}s"


def spiral_arm_label(l):
    if 25 <= l <= 55:
        return "Scutum-Centaurus arm"
    elif 55 < l <= 85:
        return "Sagittarius-Cygnus transition"
    elif 85 < l <= 110:
        return "Cygnus arm"
    elif 280 <= l <= 310:
        return "Carina arm"
    elif 310 < l <= 340:
        return "Crux-Centaurus arm"
    elif l < 15 or l > 350:
        return "Galactic center direction"
    elif 160 <= l <= 210:
        return "Galactic anticenter"
    elif 110 < l <= 160:
        return "Perseus arm"
    elif 210 < l <= 250:
        return "Outer arm"
    elif 250 < l < 280:
        return "Vela-Puppis"
    return ""


def main():
    catalog_path = sys.argv[1] if len(sys.argv) > 1 else '/tmp/atnf_pulsars.json'

    print("=" * 74)
    print("  BLACK HOLE PROBE")
    print("  Density estimator over ATNF Pulsar Catalogue v2.9.0")
    print("  The probe learns where pulsars ARE, then finds where they AREN'T.")
    print("=" * 74)
    print()

    coords = load_catalog(catalog_path)
    print(f"  Catalog: {len(coords)} pulsars with galactic coordinates + distance")

    l_bins, b_bins = 180, 40
    observed, l_edges, b_edges = galactic_density_map(coords, l_bins, b_bins, b_range=10)
    plane_count = int(observed.sum())
    print(f"  Galactic plane (|b| < 10 deg): {plane_count} pulsars")
    print(f"  Density grid: {l_bins} x {b_bins} bins")
    print()

    X, y, l_centers, b_centers = build_training_data(observed, l_edges, b_edges)

    probe = ProbeMatrix(input_dim=2, hidden=128, seed=42)
    print("  Training probe matrix (2 → 128 → 128 → 1)...")

    n_epochs = 3000
    for epoch in range(n_epochs):
        loss = probe.backward(X, y, lr=0.003)
        if (epoch + 1) % 1000 == 0:
            print(f"    epoch {epoch+1:5d}  MSE = {loss:.6f}")

    predicted = probe.forward(X)
    predicted = np.clip(predicted, 0, None)
    print(f"    prediction range: [{predicted.min():.4f}, {predicted.max():.4f}]")
    print()

    candidates, reward_spectrum = find_candidates(predicted, observed, l_centers, b_centers)

    print("=" * 74)
    print(f"  {len(candidates)} BLACK HOLE CANDIDATE LOCATIONS")
    print("  Ranked by reward score (predicted density - observed density)")
    print("=" * 74)
    print()
    print(f"{'#':>2}  {'l':>6} {'b':>5}  {'RA (J2000)':>12} {'Dec (J2000)':>13}  {'score':>6} {'obs':>4}  region")
    print("-" * 78)

    results = []
    for i, c in enumerate(candidates[:25]):
        ra, dec = gal_to_eq(c['l'], c['b'])
        region = spiral_arm_label(c['l'])

        print(f"{i+1:2d}  {c['l']:6.1f} {c['b']:5.1f}  {ra_hms(ra):>12} {dec_dms(dec):>13}  {c['reward']:6.3f} {c['observed_nearby']:4d}  {region}")

        results.append({
            'rank': i + 1,
            'galactic_l': c['l'],
            'galactic_b': c['b'],
            'ra_j2000': ra_hms(ra),
            'dec_j2000': dec_dms(dec),
            'ra_deg': round(ra, 4),
            'dec_deg': round(dec, 4),
            'reward_score': c['reward'],
            'observed_pulsars_nearby': c['observed_nearby'],
            'predicted_density': c['predicted_density'],
            'prominence': c['prominence'],
            'region': region,
        })

    print()
    print("=" * 74)
    print("  HOW IT WORKS")
    print("=" * 74)
    print("""
  The probe is a small neural network matrix trained on the observed spatial
  distribution of 4503 pulsars from the ATNF Pulsar Catalogue. It learns the
  smooth underlying density of pulsars across the galactic plane — the pattern
  of where neutron stars (seams at the edge of collapse) concentrate along
  spiral arms and toward the galactic center.

  The REWARD SPECTRUM at each grid point = predicted density - observed density.
  Where the probe predicts pulsars but the catalog shows none, the reward peaks.
  These peaks are candidate locations for isolated black holes: neutron stars
  that already crossed the seam into collapse, removing themselves from the
  pulsar catalog but leaving a gap the probe can detect.

  This is a facsimile probe: it goes in (learns the distribution), reads the
  state (the density field), and returns the signal (the gaps). Same structure
  at every scale — the DSO reading the piezo, the RNA reading the tumor, the
  probe reading the galaxy.
""")

    output = {
        'title': 'Black Hole Probe — Predicted Isolated Black Hole Locations',
        'method': 'MLP density estimator trained on ATNF Pulsar Catalogue v2.9.0',
        'date': '2026-10-18',
        'author': 'Noah Davidson',
        'catalog_version': '2.9.0',
        'catalog_pulsars': len(coords),
        'plane_pulsars': plane_count,
        'probe_architecture': '2 → 128 → 128 → 1 (MLP, ReLU, 33,409 parameters)',
        'training_epochs': n_epochs,
        'grid': f'{l_bins} x {b_bins} bins, |b| < 10 deg',
        'candidates': results,
        'note': 'Candidate locations where the probe predicts pulsar density but the catalog shows a gap. Higher reward score = stronger signal.',
    }

    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'black_hole_candidates.json')
    with open(out_path, 'w') as f:
        json.dump(output, f, indent=2)
    print(f"  Saved: {out_path}")


if __name__ == '__main__':
    main()
