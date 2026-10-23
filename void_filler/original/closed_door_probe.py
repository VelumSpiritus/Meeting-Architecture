#!/usr/bin/env python3
"""
Closed Door Probe — 2D peak detection with fifth-harmonic separation.

Same architecture as the Black Hole Probe. Same math. Different sky.

A black hole hides mass — you find it by where pulsars SHOULD be but aren't.
A closed door hides power — you find it by where public record SHOULD be but isn't.

The probe learns expected density from observable events (public records,
filings, meetings, transactions). Where the model predicts activity but
the record is silent, something met behind a closed door.

The void IS the signal. The absence IS the mass.

Separation tuned to 3:2 of bin resolution (the fifth harmonic) —
the same interval that seeds departure from the cycle.
"""

import json, math
import numpy as np
from scipy.ndimage import gaussian_filter, maximum_filter


def load_public_record(path):
    """Load observable events — the 'pulsars' of public record space."""
    with open(path) as f:
        records = json.load(f)
    events = []
    for r in records:
        if r.get('date') and r.get('sector'):
            events.append((r['date_num'], r['sector_num'], r.get('weight', 1), r.get('name', '')))
    return events


def activity_density_map(events, t_bins=360, s_bins=180, s_range=10):
    """
    Build a 2D density map of public activity.
    Axis 1: time (the longitude — where in history)
    Axis 2: sector (the latitude — which domain of power)

    Where the map is dense: public record exists, doors were open.
    Where the map is sparse: either nothing happened, or something
    happened behind a closed door.
    """
    plane = [(t, s, w) for t, s, w, _ in events if abs(s) < s_range]
    t_vals = np.array([e[0] for e in plane])
    s_vals = np.array([e[1] for e in plane])
    t_edges = np.linspace(0, 360, t_bins + 1)
    s_edges = np.linspace(-s_range, s_range, s_bins + 1)
    observed, _, _ = np.histogram2d(t_vals, s_vals, bins=[t_edges, s_edges])
    return observed, t_edges, s_edges


class ProbeMatrix:
    """
    33k-param MLP (2->128->128->1, ReLU).

    Learns what public activity SHOULD look like given time and sector.
    The same architecture that found 10 black holes in the galactic plane
    by learning where pulsars should be and finding where they aren't.

    Here it learns where public record should be and finds where it isn't.
    The gap between predicted and observed is the reward signal.
    Positive reward = the model expects activity but the record is silent.
    That silence is where power met behind a closed door.
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


def build_training_data(observed, t_edges, s_edges):
    t_centers = 0.5 * (t_edges[:-1] + t_edges[1:])
    s_centers = 0.5 * (s_edges[:-1] + s_edges[1:])
    tt, ss = np.meshgrid(t_centers, s_centers, indexing='ij')
    X = np.column_stack([tt.ravel() / 360.0, ss.ravel() / 20.0])
    y = observed.ravel().reshape(-1, 1)
    y_norm = y / (y.max() + 1e-8)
    return X, y_norm, t_centers, s_centers


def date_to_num(year, month=1, day=1):
    """Map a date to [0, 360) — one full cycle of history."""
    base_year = 1870
    span_years = 160
    frac = (year + (month - 1) / 12 + (day - 1) / 365 - base_year) / span_years
    return (frac * 360) % 360


def num_to_date(num):
    """Inverse — map [0, 360) back to a year."""
    base_year = 1870
    span_years = 160
    return base_year + (num / 360) * span_years


def sector_label(s):
    """
    The sectors of power — like spiral arms of the galaxy,
    but the galaxy here is the institutional architecture.
    """
    if -1 <= s <= 1: return "Banking / Finance"
    elif 1 < s <= 3: return "Government / Legislative"
    elif 3 < s <= 5: return "Military / Intelligence"
    elif 5 < s <= 7: return "Media / Entertainment"
    elif 7 < s <= 10: return "Technology / Infrastructure"
    elif -3 <= s < -1: return "Energy / Resources"
    elif -5 <= s < -3: return "Judiciary / Legal"
    elif -7 <= s < -5: return "Pharmaceutical / Medical"
    elif -10 <= s < -7: return "Education / Academic"
    return "Unclassified"


def find_closed_doors(predicted, observed, t_centers, s_centers, target_n=10):
    """
    Find peaks in 2D reward spectrum with fifth-harmonic separation.

    The reward signal: predicted activity minus observed record.
    Where the model says there SHOULD be public activity but the
    record is silent — that's a closed door. Power met there.
    Mass hides there. The void is the signal.

    Fifth-harmonic separation (3:2 of bin resolution):
    The same interval that seeds departure from the cycle.
    A whole cycle plus its fifth is the minimum structure
    containing both return and the seed of departure.
    The detection resonates symmetrically with the grid —
    5x5 window, same on both axes, no arbitrary bias.
    """
    pred_2d = predicted.reshape(len(t_centers), len(s_centers))

    obs_smooth = gaussian_filter(observed.astype(float), sigma=2)
    pred_smooth = gaussian_filter(pred_2d, sigma=2)

    obs_norm = obs_smooth / (obs_smooth.max() + 1e-8)
    pred_norm = pred_smooth / (pred_smooth.max() + 1e-8)

    reward = pred_norm - obs_norm

    fifth_bins = round(1.5)
    neighborhood = 2 * fifth_bins + 1
    print(f"    fifth separation: {fifth_bins} bins each axis, {neighborhood}x{neighborhood} window")

    local_max = maximum_filter(reward, size=(neighborhood, neighborhood))
    peaks_mask = (reward == local_max) & (reward > 0)

    peak_coords = np.argwhere(peaks_mask)
    peak_scores = reward[peaks_mask]

    order = np.argsort(-peak_scores)
    peak_coords = peak_coords[order]
    peak_scores = peak_scores[order]

    selected = []
    for idx in range(len(peak_coords)):
        ti, si = peak_coords[idx]
        too_close = False
        for st, ss, _, _, _ in selected:
            if abs(ti - st) < fifth_bins and abs(si - ss) < fifth_bins:
                too_close = True
                break
        if not too_close:
            obs_count = int(observed[max(0, ti-1):min(len(t_centers), ti+2),
                                     max(0, si-1):min(len(s_centers), si+2)].sum())
            selected.append((ti, si, float(peak_scores[idx]), obs_count, float(pred_2d[ti, si])))
        if len(selected) >= target_n:
            break

    print(f"    raw 2D peaks: {len(peak_coords)}, after fifth-separation: {len(selected)} (target {target_n})")

    candidates = []
    for ti, si, score, obs_count, pred_val in selected:
        year = num_to_date(float(t_centers[ti]))
        sector = float(s_centers[si])
        candidates.append({
            'time': round(float(t_centers[ti]), 1),
            'sector': round(sector, 1),
            'year': round(year, 1),
            'sector_name': sector_label(sector),
            'reward': round(score, 4),
            'observed_nearby': obs_count,
            'predicted_density': round(pred_val, 4),
        })

    return candidates


# ── DEMO: run on the meeting_trace data if it exists ──

def load_from_trace(trace_path='F:/Codebook Analysis Engine/meeting_trace/trace.json'):
    """
    Convert meeting_tracer.py's stored events into probe-format records.
    Each event/meeting becomes a data point in time x sector space.
    """
    if not __import__('pathlib').Path(trace_path).exists():
        return None

    with open(trace_path) as f:
        data = json.load(f)

    SECTOR_MAP = {
        'banking': 0, 'finance': 0, 'bank': 0, 'federal reserve': 0, 'morgan': 0,
        'government': 2, 'congress': 2, 'senate': 2, 'legislative': 2, 'huac': 2, 'hearing': 2,
        'military': 4, 'war': 4, 'intelligence': 4, 'fbi': 4, 'cia': 4,
        'media': 6, 'entertainment': 6, 'studio': 6, 'film': 6, 'television': 6,
        'technology': 8, 'wireless': 8, 'energy': -2, 'tower': -2, 'electric': -2,
        'judiciary': -4, 'legal': -4, 'court': -4, 'law': -4,
        'pharmaceutical': -6, 'medical': -6, 'death': -6,
    }

    records = []

    for mid, meeting in data.get('meetings', {}).items():
        date_str = meeting.get('date', '')
        try:
            year = int(date_str[:4])
        except (ValueError, IndexError):
            continue

        text = ' '.join([
            meeting.get('stated_purpose', ''),
            meeting.get('location', ''),
            meeting.get('delta', ''),
            ' '.join(meeting.get('names', []))
        ]).lower()

        sector = 0
        for keyword, val in SECTOR_MAP.items():
            if keyword in text:
                sector = val
                break

        records.append({
            'date_num': date_to_num(year),
            'sector_num': sector + np.random.normal(0, 0.3),
            'weight': 1,
            'name': f"MEETING: {' + '.join(meeting.get('names', [])[:3])}"
        })

    for eid, event in data.get('events', {}).items():
        date_str = event.get('date', '')
        try:
            year = int(date_str[:4])
        except (ValueError, IndexError):
            continue

        text = ' '.join([
            event.get('event', ''),
            event.get('delta', ''),
            event.get('before', ''),
            event.get('after', '')
        ]).lower()

        sector = 0
        for keyword, val in SECTOR_MAP.items():
            if keyword in text:
                sector = val
                break

        records.append({
            'date_num': date_to_num(year),
            'sector_num': sector + np.random.normal(0, 0.3),
            'weight': 1,
            'name': f"EVENT: {event.get('event', 'unknown')}"
        })

    return records


if __name__ == '__main__':
    print("=" * 92)
    print("  CLOSED DOOR PROBE")
    print("  Same architecture as the Black Hole Probe. Same math. Different sky.")
    print("  The void is the signal. The absence is the mass.")
    print("=" * 92)
    print()

    records = load_from_trace()
    if records:
        print(f"Loaded {len(records)} events from meeting trace")
        for r in records:
            year = num_to_date(r['date_num'])
            sector = sector_label(r['sector_num'])
            print(f"  {year:7.1f}  {sector:30s}  {r['name']}")
    else:
        print("No meeting trace found — run meeting_tracer.py seed first")
        print("Or supply your own public record catalog as JSON")
        print()
        print("The probe needs observable events the way the black hole probe needs pulsars.")
        print("Each event is a point in (time x sector) space.")
        print("The model learns where events cluster.")
        print("Where it predicts activity but the record is silent — that's the closed door.")
        print()
        print("FORMAT: [{date_num: 0-360, sector_num: -10 to 10, weight: 1, name: '...'}]")
        print()
        print("SECTORS:")
        for s in range(-9, 10, 2):
            print(f"  {s:+3d}  {sector_label(s)}")

    print()
    print("=" * 92)
    print("  The meeting is the unit. The void is the signal.")
    print("  Where the record should speak and doesn't — power met behind a closed door.")
    print("  The same math that finds where mass hides stars")
    print("  finds where power hides meetings.")
    print("=" * 92)
