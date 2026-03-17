# Coupling Status

This repository now has:

- `fluidCase/`: 3D rigid round-pipe droplet transport using `incompressibleVoF`
- `solidCase/`: deformable pipe-wall shell using `solidDisplacement`

What it does not yet have:

- two-way FSI coupling between the fluid and solid
- moving fluid mesh driven by wall displacement
- pressure/shear transfer from the fluid wall patch to the solid inner wall

## What is currently correct

The setup is correct as a pre-FSI split:

- `fluidCase` gives the fluid-side droplet transport baseline.
- `solidCase` gives a deformable pipe-wall baseline under prescribed internal pressure.

## What is missing for complete flexible-pipe FSI

To make this a fully coupled flexible pipe simulation, the project still needs:

1. Interface data transfer from `fluidCase/pipeWall` to `solidCase/innerWall`
2. Mesh motion on the fluid case using the resulting wall displacement
3. Time-step coupling iterations between the fluid and solid solves
4. A coupling framework or custom workflow to enforce 1-3 robustly

Without those pieces, the repository should be treated as:

- complete rigid fluid case
- complete standalone deformable wall case
- incomplete coupled flexible-pipe FSI

