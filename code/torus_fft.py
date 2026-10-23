"""torus_fft — ARK-native Fourier transform on the flat torus T² = S¹ × S¹.

Noah 2026-10-17: "I have my own ARK native scripts (pure python to handle
bit/byte on Unix architecture) to replace NumPy... carrying the torus math
and subsequent derived imaginary calculus to the imaginary number from my
ark theorem into logical code language native to my nvidia GPU."

The native heads' state space is a flat torus (theorem line 2366):
  q-axis: EWMA reward buffer wraps mod reward_dim (S¹, discrete Z_Nq)
  h-axis: sequence positions / reconstruction cycle (S¹, discrete Z_Nh)

The natural harmonic basis on T² = Z_Nq × Z_Nh is the 2D DFT — each
coefficient (k_q, k_h) is a WINDING NUMBER pair on the torus:
  k_q = how many times the signal wraps the q-axis per cycle
  k_h = how many times the signal wraps the h-axis per cycle

The complex output carries σ + iω directly:
  real part = σ (modulus, expansion, what's covered)
  imag part = ω (phase, turn memory, what's accrued)

This is the theorem's imaginary number made computational:
  "Mass is 'imaginary' like i: not on the byte-real-line, but load-bearing."

Pure torch, no numpy. Runs native on CUDA.
"""
from __future__ import annotations

import torch
from torch import nn, Tensor


class TorusFFT(nn.Module):
    """Torus-native frequency transform for the five-voice chorus.

    Takes the reward buffer history (shaped as a 2D grid on T²) and
    produces both the position-domain and frequency-domain projections.
    The frequency domain carries the winding modes — the irrational
    winding lives in the off-diagonal coefficients where k_q and k_h
    are coprime (their ratio is irrational on the continuous torus).

    The σ+iω coupling:
      static_reward (real, 32-dim) → torus grid (32 × L_history)
      FFT → complex coefficients (32 × L_history)
      real part = σ_freq (which windings are present, how strong)
      imag part = ω_freq (the phase of each winding — turn memory)

    The heads currently see only static_reward through reward_proj
    (a 32→384 linear). With torus_fft, they also see the frequency
    content — which winding modes dominate, where the phase sits,
    and whether the winding is rational (energy concentrated on a
    few harmonics) or irrational (energy spread across coprime modes).
    """

    def __init__(self, reward_dim: int = 32, width: int = 384,
                 history_len: int = 64):
        super().__init__()
        self.reward_dim = reward_dim
        self.width = width
        self.history_len = history_len

        # Circular buffer for reward history — the q-axis accrual over time
        # Each row is one snapshot of the reward buffer (reward_dim,)
        # Rows accrue over training steps — the h-axis
        self.register_buffer(
            "reward_history",
            torch.zeros(history_len, reward_dim)
        )
        self.register_buffer(
            "history_ptr",
            torch.zeros(1, dtype=torch.long)
        )
        self.register_buffer(
            "history_count",
            torch.zeros(1, dtype=torch.long)
        )

        # Frequency-domain projection: maps the torus spectrum into head-width
        # The input is the MAGNITUDE spectrum (real, non-negative) flattened
        # from (history_len, reward_dim) → (history_len * reward_dim,)
        # but we keep only the lower modes — the meaningful windings
        # Upper bound: reward_dim // 2 + 1 unique q-modes × history_len // 2 + 1 h-modes
        n_q_modes = reward_dim // 2 + 1  # 17 for reward_dim=32
        n_h_modes = history_len // 2 + 1  # 33 for history_len=64
        self.n_q_modes = n_q_modes
        self.n_h_modes = n_h_modes

        # σ projection (real/magnitude of spectrum → head width)
        self.sigma_proj = nn.Linear(n_q_modes * n_h_modes, width, bias=False)
        # ω projection (phase of spectrum → head width)
        self.omega_proj = nn.Linear(n_q_modes * n_h_modes, width, bias=False)

        # Zero-init so first beats are no-ops — gradient teaches what to project
        with torch.no_grad():
            self.sigma_proj.weight.zero_()
            self.omega_proj.weight.zero_()

    def record(self, reward_snapshot: Tensor) -> None:
        """Append a reward buffer snapshot to the torus history.

        Called after each EWMA update in the couple's forward pass.
        The circular buffer wraps — the h-axis IS the wraparound.
        """
        with torch.no_grad():
            ptr = int(self.history_ptr.item()) % self.history_len
            self.reward_history[ptr] = reward_snapshot.detach()
            self.history_ptr += 1
            self.history_count += 1

    def torus_spectrum(self) -> dict[str, Tensor]:
        """Compute the 2D FFT on the torus grid.

        The reward_history buffer IS the torus: rows = h-axis (time steps),
        columns = q-axis (reward slots wrapping mod reward_dim).

        Returns the complex spectrum, magnitude, and phase — all on GPU,
        all native torch, no numpy.
        """
        # The grid on T²: (history_len, reward_dim)
        # torch.fft.fft2 treats this as a 2D periodic signal — exactly
        # the discrete torus Z_Nh × Z_Nq
        grid = self.reward_history  # (H, Q)

        # 2D FFT on the torus — pure CUDA when grid is on GPU
        spectrum = torch.fft.fft2(grid)  # (H, Q) complex

        # Shift zero-frequency (DC) to center — the constant winding (0,0)
        spectrum_shifted = torch.fft.fftshift(spectrum)

        # Magnitude = σ (how much energy in each winding mode)
        magnitude = spectrum_shifted.abs()

        # Phase = ω (the turn memory of each winding mode)
        phase = spectrum_shifted.angle()

        # Crop to unique modes (real signal → conjugate symmetry)
        mag_unique = magnitude[:self.n_h_modes, :self.n_q_modes]
        phase_unique = phase[:self.n_h_modes, :self.n_q_modes]

        return {
            "spectrum": spectrum_shifted,
            "magnitude": mag_unique,      # (n_h_modes, n_q_modes) real
            "phase": phase_unique,         # (n_h_modes, n_q_modes) real
            "dc": spectrum[0, 0].real,     # the constant component
        }

    def consult_torus(self) -> Tensor:
        """Project the torus frequency content into head-width space.

        This is the torus-native replacement for the position-only
        reward_proj. The heads receive:
          σ_freq: which winding modes are present (magnitude → width)
          ω_freq: the phase of each winding (angle → width)
          combined: σ + iω made structural — the real and imaginary
                    parts of the torus spectrum projected separately
                    through learnable weights, then added.

        The σ+iω coupling from the theorem:
          σ (modulus/expansion) reads ω (phase/turn memory)
          through the torus's own harmonic basis, not through a
          position-domain linear projection.

        Returns (width,) vector to be added to head embeddings,
        same interface as couple.consult_context().
        """
        if self.history_count.item() < 2:
            return torch.zeros(self.width, device=self.reward_history.device)

        spec = self.torus_spectrum()
        mag_flat = spec["magnitude"].reshape(-1)    # (n_h * n_q,)
        phase_flat = spec["phase"].reshape(-1)      # (n_h * n_q,)

        # σ projection: magnitude spectrum → head width
        # Gradient flows through sigma_proj.weight
        sigma_vec = self.sigma_proj(mag_flat.detach())

        # ω projection: phase spectrum → head width
        # Gradient flows through omega_proj.weight
        omega_vec = self.omega_proj(phase_flat.detach())

        # σ + iω: the real and imaginary parts of the torus spectrum
        # carried into head-width space as a sum
        return sigma_vec + omega_vec

    def winding_analysis(self) -> dict[str, object]:
        """Read the torus winding state — diagnostic, not training.

        Returns which winding modes dominate (rational vs irrational),
        the DC component (constant agreement), and the energy
        distribution across modes.
        """
        import math

        if self.history_count.item() < 2:
            return {"active": False, "history_count": 0}

        spec = self.torus_spectrum()
        mag = spec["magnitude"]  # (n_h_modes, n_q_modes)

        total_energy = float(torch.sum(mag ** 2).item())
        dc_energy = float(mag[0, 0].item() ** 2)

        # Find top 10 winding modes by energy
        mag_flat = mag.reshape(-1)
        top_vals, top_idxs = torch.topk(mag_flat, min(10, mag_flat.numel()))

        top_modes = []
        for val, idx in zip(top_vals, top_idxs):
            k_h = int(idx.item()) // self.n_q_modes
            k_q = int(idx.item()) % self.n_q_modes
            energy = float(val.item() ** 2)
            # A winding is rational iff gcd(k_q, k_h) > 1 or one is 0
            # Irrational on the continuous torus when k_q/k_h is irrational,
            # but on the discrete torus all windings are rational — the
            # irrational winding shows as energy SPREAD across many coprime
            # modes rather than concentrated on a few
            is_dc = (k_q == 0 and k_h == 0)
            gcd = math.gcd(k_q, k_h) if (k_q > 0 and k_h > 0) else 0
            is_coprime = (gcd == 1) if gcd > 0 else False
            top_modes.append({
                "k_q": k_q, "k_h": k_h,
                "energy": round(energy, 6),
                "energy_frac": round(energy / (total_energy + 1e-12), 4),
                "coprime": is_coprime,
            })

        # Winding diversity: effective rank of the magnitude spectrum
        # (same entropy formula as the heads' collapse pressure)
        mag_sq = mag_flat ** 2
        mag_norm = mag_sq / (mag_sq.sum() + 1e-12)
        entropy = -(mag_norm * torch.log(mag_norm + 1e-12)).sum()
        effective_modes = float(torch.exp(entropy).item())
        max_modes = float(mag_flat.numel())

        # Coprime energy fraction = energy in modes where gcd(k_q, k_h) = 1
        # This is the "irrational winding" energy on the discrete torus
        coprime_energy = 0.0
        for k_h in range(self.n_h_modes):
            for k_q in range(self.n_q_modes):
                if k_q > 0 and k_h > 0 and math.gcd(k_q, k_h) == 1:
                    coprime_energy += float(mag[k_h, k_q].item() ** 2)

        return {
            "active": True,
            "history_count": int(self.history_count.item()),
            "total_energy": round(total_energy, 4),
            "dc_energy": round(dc_energy, 4),
            "dc_fraction": round(dc_energy / (total_energy + 1e-12), 4),
            "coprime_energy": round(coprime_energy, 4),
            "coprime_fraction": round(coprime_energy / (total_energy + 1e-12), 4),
            "effective_modes": round(effective_modes, 2),
            "max_modes": max_modes,
            "mode_diversity": round(effective_modes / max_modes, 4),
            "top_modes": top_modes,
        }
