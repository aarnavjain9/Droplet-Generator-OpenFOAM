#!/usr/bin/env python3
"""Reduced-order droplet generator simulation in laminar pipe flow.

The model tracks a scalar phase fraction field for a dispersed liquid injected
through a nozzle into a carrier flow. It is not a full Navier-Stokes solver;
instead it combines:

- prescribed Poiseuille flow in a 2D pipe cross-section
- periodic injection pulses at the inlet
- explicit upwind advection of the dispersed phase
- small diffusion to regularize the interface

This is useful as a fast starting point for exploring how pulse timing, nozzle
size, and pipe velocity influence droplet spacing and transport.
"""

from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", str(Path(".mplconfig").resolve()))

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.animation import FuncAnimation, PillowWriter


@dataclass
class SimulationConfig:
    length: float = 0.05
    radius: float = 0.002
    nx: int = 320
    ny: int = 96
    total_time: float = 0.12
    cfl: float = 0.35
    umax: float = 0.12
    diffusivity: float = 1.5e-7
    nozzle_radius: float = 0.00045
    nozzle_x: float = 0.0015
    pulse_period: float = 0.014
    duty_cycle: float = 0.32
    injection_strength: float = 28.0
    purge_strength: float = 18.0
    frame_stride: int = 12
    output_dir: str = "output"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--length", type=float, default=SimulationConfig.length)
    parser.add_argument("--radius", type=float, default=SimulationConfig.radius)
    parser.add_argument("--nx", type=int, default=SimulationConfig.nx)
    parser.add_argument("--ny", type=int, default=SimulationConfig.ny)
    parser.add_argument("--total-time", type=float, default=SimulationConfig.total_time)
    parser.add_argument("--cfl", type=float, default=SimulationConfig.cfl)
    parser.add_argument("--umax", type=float, default=SimulationConfig.umax)
    parser.add_argument("--diffusivity", type=float, default=SimulationConfig.diffusivity)
    parser.add_argument("--nozzle-radius", type=float, default=SimulationConfig.nozzle_radius)
    parser.add_argument("--nozzle-x", type=float, default=SimulationConfig.nozzle_x)
    parser.add_argument("--pulse-period", type=float, default=SimulationConfig.pulse_period)
    parser.add_argument("--duty-cycle", type=float, default=SimulationConfig.duty_cycle)
    parser.add_argument(
        "--injection-strength",
        type=float,
        default=SimulationConfig.injection_strength,
        help="Relaxation rate toward phi=1 inside the nozzle when the pulse is on.",
    )
    parser.add_argument(
        "--purge-strength",
        type=float,
        default=SimulationConfig.purge_strength,
        help="Relaxation rate toward phi=0 in the nozzle between pulses to keep droplets separated.",
    )
    parser.add_argument("--frame-stride", type=int, default=SimulationConfig.frame_stride)
    parser.add_argument("--output-dir", default=SimulationConfig.output_dir)
    return parser


def poiseuille_profile(y: np.ndarray, radius: float, umax: float) -> np.ndarray:
    return umax * np.clip(1.0 - (y / radius) ** 2, 0.0, None)


def laplacian(field: np.ndarray, dx: float, dy: float) -> np.ndarray:
    padded = np.pad(field, ((1, 1), (1, 1)), mode="edge")
    d2x = (padded[1:-1, 2:] - 2.0 * padded[1:-1, 1:-1] + padded[1:-1, :-2]) / dx**2
    d2y = (padded[2:, 1:-1] - 2.0 * padded[1:-1, 1:-1] + padded[:-2, 1:-1]) / dy**2
    return d2x + d2y


def advect_upwind(phi: np.ndarray, u: np.ndarray, dt: float, dx: float) -> np.ndarray:
    left = np.pad(phi[:, :-1], ((0, 0), (1, 0)), mode="edge")
    right = np.pad(phi[:, 1:], ((0, 0), (0, 1)), mode="edge")
    grad_minus = (phi - left) / dx
    grad_plus = (right - phi) / dx
    return phi - dt * np.where(u >= 0.0, u * grad_minus, u * grad_plus)


def run_simulation(config: SimulationConfig) -> tuple[np.ndarray, list[np.ndarray], np.ndarray, np.ndarray]:
    x = np.linspace(0.0, config.length, config.nx)
    y = np.linspace(-config.radius, config.radius, config.ny)
    dx = x[1] - x[0]
    dy = y[1] - y[0]
    u = poiseuille_profile(y[:, None], config.radius, config.umax)
    inlet_profile = np.where(np.abs(y) <= config.nozzle_radius, 1.0, 0.0)

    dt_adv = config.cfl * dx / max(config.umax, 1e-12)
    dt_diff = 0.25 / max(config.diffusivity * (1.0 / dx**2 + 1.0 / dy**2), 1e-12)
    dt = min(dt_adv, dt_diff, config.total_time / 600.0)
    steps = max(1, int(np.ceil(config.total_time / dt)))
    dt = config.total_time / steps

    X, Y = np.meshgrid(x, y)
    nozzle_mask = (X <= config.nozzle_x) & (np.abs(Y) <= config.nozzle_radius)
    phi = np.zeros((config.ny, config.nx), dtype=float)
    frames: list[np.ndarray] = []
    history = np.zeros((steps, config.nx), dtype=float)

    for step in range(steps):
        t = step * dt
        pulse_phase = (t % config.pulse_period) / config.pulse_period
        pulse_on = pulse_phase <= config.duty_cycle

        phi = advect_upwind(phi, u, dt, dx)
        phi += config.diffusivity * dt * laplacian(phi, dx, dy)

        if pulse_on:
            phi[nozzle_mask] += config.injection_strength * dt * (1.0 - phi[nozzle_mask])
        elif config.purge_strength > 0.0:
            phi[nozzle_mask] -= config.purge_strength * dt * phi[nozzle_mask]

        if pulse_on:
            phi[:, 0] = inlet_profile
        else:
            phi[:, 0] = 0.0
        phi[:, -1] = phi[:, -2]
        phi[0, :] = 0.0
        phi[-1, :] = 0.0
        phi = np.clip(phi, 0.0, 1.0)

        history[step] = phi.mean(axis=0)
        if step % max(config.frame_stride, 1) == 0 or step == steps - 1:
            frames.append(phi.copy())

    return phi, frames, x, y


def save_summary(config: SimulationConfig, frames: list[np.ndarray], x: np.ndarray, y: np.ndarray) -> None:
    output_dir = Path(config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    final_phi = frames[-1]
    fig, ax = plt.subplots(figsize=(11, 3.2), constrained_layout=True)
    image = ax.imshow(
        final_phi,
        origin="lower",
        extent=[x.min() * 1e3, x.max() * 1e3, y.min() * 1e3, y.max() * 1e3],
        cmap="Blues",
        vmin=0.0,
        vmax=1.0,
        aspect="auto",
    )
    ax.set_title("Droplet Volume Fraction in Pipe")
    ax.set_xlabel("Axial position x [mm]")
    ax.set_ylabel("Radial position y [mm]")
    fig.colorbar(image, ax=ax, label="Dispersed phase fraction")
    fig.savefig(output_dir / "droplet_pipe_snapshot.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(11, 3.2), constrained_layout=True)
    centroids = np.array([frame.mean(axis=0) for frame in frames])
    image = ax.imshow(
        centroids,
        origin="lower",
        extent=[x.min() * 1e3, x.max() * 1e3, 0, len(frames)],
        cmap="magma",
        aspect="auto",
    )
    ax.set_title("Axial Transport History")
    ax.set_xlabel("Axial position x [mm]")
    ax.set_ylabel("Stored frame index")
    fig.colorbar(image, ax=ax, label="Cross-section averaged phase fraction")
    fig.savefig(output_dir / "droplet_pipe_history.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(11, 3.2), constrained_layout=True)
    image = ax.imshow(
        frames[0],
        origin="lower",
        extent=[x.min() * 1e3, x.max() * 1e3, y.min() * 1e3, y.max() * 1e3],
        cmap="Blues",
        vmin=0.0,
        vmax=1.0,
        aspect="auto",
        animated=True,
    )
    ax.set_title("Droplet Generator Animation")
    ax.set_xlabel("Axial position x [mm]")
    ax.set_ylabel("Radial position y [mm]")

    def update(frame: np.ndarray):
        image.set_array(frame)
        return (image,)

    animation = FuncAnimation(fig, update, frames=frames, interval=90, blit=True)
    try:
        animation.save(output_dir / "droplet_pipe.gif", writer=PillowWriter(fps=12))
    except Exception as exc:  # pragma: no cover - fallback for missing pillow.
        print(f"Skipping GIF export: {exc}")
    plt.close(fig)


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    config = SimulationConfig(
        length=args.length,
        radius=args.radius,
        nx=args.nx,
        ny=args.ny,
        total_time=args.total_time,
        cfl=args.cfl,
        umax=args.umax,
        diffusivity=args.diffusivity,
        nozzle_radius=args.nozzle_radius,
        nozzle_x=args.nozzle_x,
        pulse_period=args.pulse_period,
        duty_cycle=args.duty_cycle,
        injection_strength=args.injection_strength,
        purge_strength=args.purge_strength,
        frame_stride=args.frame_stride,
        output_dir=args.output_dir,
    )
    _, frames, x, y = run_simulation(config)
    save_summary(config, frames, x, y)
    print(f"Saved outputs to {Path(config.output_dir).resolve()}")


if __name__ == "__main__":
    main()
