# Flexible Pipe Upgrade Path

## What should be used for a flexible pipe

For an actual flexible pipe in OpenFOAM 13, the correct model is two-way
fluid-structure interaction:

- fluid solver: `foamRun -solver incompressibleVoF`
- solid solver: `foamRun -solver solidDisplacement`
- coupling: pressure and viscous load from fluid to solid, displacement from
  solid back to fluid

This is fundamentally different from:

- changing a wall boundary condition
- using a slip wall
- visualizing a rigid pipe transparently in ParaView

Those do not simulate pipe flexibility.

## What is available locally

This machine has:

- OpenFOAM 13 `incompressibleVoF`
- OpenFOAM 13 `solidDisplacement`

This repository does not currently have:

- a coupled FSI case
- a custom coupled solver
- a preCICE-based coupling setup
- solids4foam case files

## Recommended repo structure for the real flexible version

Use two cases instead of trying to overload one directory:

- `fluidCase/`
  Purpose: droplet flow in the fluid domain
- `solidCase/`
  Purpose: pipe wall deformation
- `coupling/`
  Purpose: interface mapping, run scripts, and shared geometry definitions

## Suggested implementation plan

1. Keep the current rigid 3D pipe case as the reference fluid-only case.
2. Create a pipe-wall solid mesh with realistic thickness and material model.
3. Define interface patches between fluid and wall.
4. Add mesh motion for the fluid side driven by wall displacement.
5. Add staggered or strongly coupled iteration between fluid and solid each
   time step.
6. Validate with a simple pressure pulse before enabling droplet transport.

## Practical note

If you want a quick approximation before full FSI, the nearest honest
intermediate step is prescribed wall motion:

- deform the pipe with a known motion law
- move the fluid mesh accordingly
- still treat it as one-way motion, not true flexibility

That is useful for debugging mesh motion, but it is not the same as a flexible
pipe responding to the droplet flow.
