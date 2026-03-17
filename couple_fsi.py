#!/usr/bin/env python3
import os
import subprocess
import shutil
import re

def run_command(command, cwd):
    print(f"Running: {command} in {cwd}")
    result = subprocess.run(command, shell=True, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error running command: {command}")
        print(result.stderr)
        return False
    return True

def get_latest_pressure(fluid_case_dir):
    pressure_file = os.path.join(fluid_case_dir, "postProcessing", "patchAveragePressure", "0", "surfaceFieldValue.dat")
    if not os.path.exists(pressure_file):
        # Check for other time directories if 0 is not there
        times = sorted([d for d in os.listdir(os.path.join(fluid_case_dir, "postProcessing", "patchAveragePressure")) if os.path.isdir(os.path.join(fluid_case_dir, "postProcessing", "patchAveragePressure", d))], key=float)
        if not times:
            return 0.0
        pressure_file = os.path.join(fluid_case_dir, "postProcessing", "patchAveragePressure", times[-1], "surfaceFieldValue.dat")
    
    with open(pressure_file, 'r') as f:
        lines = f.readlines()
        for line in reversed(lines):
            if line.startswith('#') or not line.strip():
                continue
            parts = line.split()
            if len(parts) >= 2:
                return float(parts[1])
    return 0.0

def update_solid_pressure(solid_case_dir, pressure):
    d_file = os.path.join(solid_case_dir, "0", "D")
    with open(d_file, 'r') as f:
        content = f.read()
    
    # Update innerWall pressure
    new_content = re.sub(
        r'(innerWall\s*{[^}]*pressure\s+uniform\s+)\d+(\.\d+)?',
        rf'\g<1>{pressure}',
        content
    )
    
    with open(d_file, 'w') as f:
        f.write(new_content)

def main():
    base_dir = os.getcwd()
    fluid_dir = os.path.join(base_dir, "fluidCase")
    solid_dir = os.path.join(base_dir, "solidCase")
    
    # 1. Clean and Setup
    print("Setting up cases...")
    run_command("./Allclean", fluid_dir)
    run_command("./Allclean", solid_dir)
    run_command("blockMesh", fluid_dir)
    run_command("cp -r constant/polyMesh 0/", fluid_dir)
    run_command("setFields", fluid_dir)
    run_command("blockMesh", solid_dir)
    run_command("cp -r constant/polyMesh 0/", solid_dir)

    total_time = 0.12
    dt = 0.001
    current_time = 0.0
    
    while current_time < total_time:
        next_time = round(current_time + dt, 6)
        print(f"\n--- Coupling Time Step: {next_time} ---")
        
        # Update controlDicts for next step
        # Fluid
        with open(os.path.join(fluid_dir, "system", "controlDict"), 'r') as f:
            content = f.read()
        content = re.sub(r'endTime\s+\d+(\.\d+)?', f'endTime {next_time}', content)
        with open(os.path.join(fluid_dir, "system", "controlDict"), 'w') as f:
            f.write(content)
            
        # Solid
        with open(os.path.join(solid_dir, "system", "controlDict"), 'r') as f:
            content = f.read()
        content = re.sub(r'endTime\s+\d+(\.\d+)?', f'endTime {next_time}', content)
        with open(os.path.join(solid_dir, "system", "controlDict"), 'w') as f:
            f.write(content)
            
        # 2. Run Fluid
        if not run_command("foamRun -solver incompressibleVoF", fluid_dir):
            break
            
        # 3. Extract Pressure
        avg_p = get_latest_pressure(fluid_dir)
        print(f"Extracted average pressure: {avg_p}")
        
        # 4. Update Solid Pressure
        update_solid_pressure(solid_dir, avg_p)
        
        # 5. Run Solid
        if not run_command("foamRun -solver solidDisplacement", solid_dir):
            break
            
        current_time = next_time

if __name__ == "__main__":
    main()
