#!/usr/bin/env python3
"""Realistic PDMS Pipe FSI: Water droplets in Silicone Oil with smooth wall coupling."""

import os
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter
from dataclasses import dataclass
from pathlib import Path

@dataclass
class FSIConfig:
    length: float = 0.06
    radius: float = 0.002
    nx: int = 500  # Higher resolution for smoothness
    ny: int = 120
    total_time: float = 0.8
    umax: float = 0.12 
    # PDMS Material Properties (Soft Elastomer)
    E_pdms: float = 2.0e6 
    compliance: float = 1.0e-6 
    pulse_period: float = 0.2
    output_dir: str = "output_fsi"

def run_fsi_simulation(cfg: FSIConfig):
    x = np.linspace(0, cfg.length, cfg.nx)
    y = np.linspace(-cfg.radius, cfg.radius, cfg.ny)
    X, Y = np.meshgrid(x, y)
    dt = 0.0004
    steps = int(cfg.total_time / dt)
    
    droplets = [] 
    displacement = np.zeros(cfg.nx)
    frames, wall_history = [], []

    # Spatial smoothing kernel for PDMS elasticity (Gaussian)
    kernel_size = 20
    kernel = np.exp(-np.linspace(-2, 2, kernel_size)**2)
    kernel /= kernel.sum()

    for step in range(steps):
        t = step * dt
        
        # 1. Injection
        if (t % cfg.pulse_period) < dt:
            droplets.append([0.0, cfg.radius * 0.65])
        
        # 2. Lagrangian Movement
        for d in droplets:
            idx = np.clip(np.searchsorted(x, d[0]), 0, cfg.nx-1)
            u_eff = cfg.umax * (cfg.radius / (cfg.radius + displacement[idx]))**2
            d[0] += u_eff * dt
        
        droplets = [d for d in droplets if d[0] < cfg.length + 0.01]

        # 3. Render Deformable Droplets
        phi = np.zeros((cfg.ny, cfg.nx))
        for d_x, R0 in droplets:
            idx = np.clip(np.searchsorted(x, d_x), 0, cfg.nx-1)
            # Droplet shape interacts with the LOCAL wall displacement
            b = R0 + displacement[idx] * 0.85 
            a = (R0**2) / b
            dist_sq = ((X - d_x)/a)**2 + ((Y - 0)/b)**2
            phi[dist_sq < 1.0] = 1.0

        # 4. PDMS Wall Response (WITH SPATIAL SMOOTHING)
        # Raw pressure from droplets
        raw_target = phi.mean(axis=0) * 1600 * cfg.compliance
        # Apply Gaussian smoothing to simulate elastic continuity of PDMS
        smooth_target = np.convolve(raw_target, kernel, mode='same')
        displacement = 0.94 * displacement + 0.06 * smooth_target
        
        if step % 25 == 0:
            frames.append(phi.copy())
            wall_history.append(displacement.copy())
            
    return x, y, frames, wall_history

def animate_fsi(x, y, frames, wall_history, cfg):
    fig, ax = plt.subplots(figsize=(15, 3.5))
    # Anti-aliased droplet rendering
    img = ax.imshow(frames[0], extent=[0, cfg.length*1e3, -cfg.radius*1e3, cfg.radius*1e3], 
                    origin='lower', cmap='Blues', aspect='equal', vmin=0, vmax=1, interpolation='bicubic')
    
    line_top, = ax.plot(x*1e3, (cfg.radius + wall_history[0])*1e3, color='#e84118', lw=2.5, label='Smooth PDMS Wall')
    line_bot, = ax.plot(x*1e3, (-cfg.radius - wall_history[0])*1e3, color='#e84118', lw=2.5)
    
    ax.set_title("Realistic FSI: Water Droplets in Silicone Oil (PDMS Pipe)")
    ax.set_xlabel("Axial Position [mm]")
    ax.set_ylabel("Y [mm]")
    ax.set_ylim(-cfg.radius*1.8e3, cfg.radius*1.8e3)
    ax.legend(loc='upper right')

    def update(i):
        img.set_array(frames[i])
        line_top.set_ydata((cfg.radius + wall_history[i])*1e3)
        line_bot.set_ydata((-cfg.radius - wall_history[i])*1e3)
        return img, line_top, line_bot

    ani = FuncAnimation(fig, update, frames=len(frames), blit=True)
    out_path = Path(cfg.output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    print("Generating smooth PDMS-Water animation...")
    ani.save(str(out_path / "fsi_animation.gif"), writer='pillow', fps=20)
    print(f"Success! Concept visualization at {out_path.resolve()}")

if __name__ == "__main__":
    animate_fsi(*run_fsi_simulation(FSIConfig()), FSIConfig())
