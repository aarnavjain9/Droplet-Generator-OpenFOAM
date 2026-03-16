# Droplet Flow Through a Pipe

This repository currently contains:

- a reduced-order Python model for quick droplet-train exploration
- `fluidCase/`: a verified OpenFOAM 13 3D round-pipe VOF case for rigid-wall droplet transport
- `solidCase/`: a standalone OpenFOAM 13 `solidDisplacement` pipe-wall case

It still does not contain true two-way flexible-pipe FSI coupling.

## Current OpenFOAM layout

### `fluidCase/`

The fluid case is a rigid cylindrical pipe with:

- a real 3D round mesh from `blockMesh`
- water-air VOF transport using `foamRun -solver incompressibleVoF`
- a spherical initialized droplet from `setFields`
- laminar flow, no-slip wall, pressure outlet

Relevant files:

- [fluidCase/system/blockMeshDict](/home/aarnav/Desktop/pipe_multiphase/fluidCase/system/blockMeshDict)
- [fluidCase/system/setFieldsDict](/home/aarnav/Desktop/pipe_multiphase/fluidCase/system/setFieldsDict)
- [fluidCase/system/controlDict](/home/aarnav/Desktop/pipe_multiphase/fluidCase/system/controlDict)
- [fluidCase/0/U](/home/aarnav/Desktop/pipe_multiphase/fluidCase/0/U)
- [fluidCase/0/alpha.water](/home/aarnav/Desktop/pipe_multiphase/fluidCase/0/alpha.water)

### `solidCase/`

The solid case is a deformable pipe-wall shell with:

- `foamRun -solver solidDisplacement`
- fixed pipe ends
- internal pressure load on the inner wall
- rubber-like elastic properties for a flexible-tube baseline

Relevant files:

- [solidCase/system/blockMeshDict](/home/aarnav/Desktop/pipe_multiphase/solidCase/system/blockMeshDict)
- [solidCase/constant/physicalProperties](/home/aarnav/Desktop/pipe_multiphase/solidCase/constant/physicalProperties)
- [solidCase/0/D](/home/aarnav/Desktop/pipe_multiphase/solidCase/0/D)

## Run the fluid case

Use:

```bash
cd fluidCase
```

```bash
./Allrun
```

Manual equivalent:

```bash
blockMesh
```

```bash
cp -r constant/polyMesh 0/
```

```bash
setFields
```

```bash
foamRun -solver incompressibleVoF
```

Open in ParaView:

```bash
paraFoam
```

To isolate the droplet in ParaView:

1. Click `Apply`
2. Color by `alpha.water`
3. Add `Threshold`
4. Set threshold range to `0.5` to `1`

## Run the solid wall case

```bash
cd solidCase
```

```bash
./Allrun
```

This runs `blockMesh` and then `foamRun -solver solidDisplacement`.

## Run both baselines

```bash
./AllcleanFlexiblePrep
```

```bash
./AllrunFlexiblePrep
```

This runs:

- the fluid droplet transport baseline in `fluidCase/`
- the deformable wall baseline in `solidCase/`

It is still a preparation workflow, not coupled FSI.

## Flexible pipe: what is actually needed

A flexible pipe is not just a different wall boundary condition. It is a
fluid-structure interaction problem:

- fluid domain: `incompressibleVoF` or another multiphase fluid solver
- solid domain: `solidDisplacement`
- interface coupling: transfer pressure/shear from fluid to wall and wall
  displacement back to the fluid mesh

This OpenFOAM 13 install includes the `solidDisplacement` module, and the repo
now includes a standalone `solidCase/`. What is still missing is the actual
fluid-solid coupling infrastructure needed for a true deforming pipe.


## What “flexible” would mean here

For this project, the technically correct upgrade path is:

1. Use `fluidCase/` as the baseline droplet-transport case.
2. Use `solidCase/` as the baseline deformable-wall case.
3. Add a coupling strategy between the fluid and the wall.
4. Move the fluid mesh with wall deformation each time step.

Until that is implemented, the OpenFOAM case in this repo should be treated as
rigid-wall only.

## Python model

The Python script remains a reduced-order exploratory model:

```bash
python3 droplet_pipe_sim.py
```

Optional example:

```bash
python3 droplet_pipe_sim.py \
  --umax 0.16 \
  --pulse-period 0.010 \
  --duty-cycle 0.25 \
  --nozzle-radius 0.00035 \
  --output-dir output_fast
```
