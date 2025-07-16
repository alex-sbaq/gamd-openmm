#!/usr/bin/env python
"""
Test script to validate that the NaN bug fix works correctly in GaMD boost calculations.

This test specifically checks for the NaN errors that occurred when:
1. windowCount = 1 (insufficient statistics for variance calculation)
2. Vmax = Vmin (no energy variation)
3. sigmaV = 0 (zero variance)

The test creates a minimal system and runs integration steps to trigger these edge cases.
"""
import sys
import os

# Add the parent directory to the path to import gamd
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import openmm.app as app
import openmm.unit as unit
import openmm
from gamd.integrator_factory import create_lower_total_boost_integrator

def test_nan_fix():
    """
    Test that GaMD boost calculations don't produce NaN values in edge cases.
    
    This test specifically targets the scenarios that previously caused NaN errors:
    - windowCount = 1 (insufficient statistics)
    - Vmax = Vmin (no energy variation)  
    - sigmaV = 0 (zero variance)
    """
    
    # Create a simple system
    topology = app.Topology()
    positions = []
    system = openmm.System()

    # Add a single particle
    chain = topology.addChain()
    residue = topology.addResidue('TES', chain)
    atom = topology.addAtom('T', app.Element.getBySymbol('C'), residue)
    positions.append([0.0, 0.0, 0.0] * unit.nanometers)
    system.addParticle(1.0)

    # Add a harmonic force to prevent trivial potential
    force = openmm.HarmonicBondForce()
    system.addForce(force)

    # Set up the integrator with parameters that will trigger the issue
    temperature = 300.0 * unit.kelvin
    dt = 2.0 * unit.femtoseconds
    
    # Use parameters that will trigger the windowCount=1 scenario
    ntcmdprep = 10
    ntcmd = 100  # Must be multiple of ntave
    ntebprep = 10
    nteb = 100   # Must be multiple of ntave
    nstlim = 300
    ntave = 20
    
    result = create_lower_total_boost_integrator(
        system, temperature, dt, ntcmdprep, ntcmd, ntebprep, nteb, nstlim, ntave
    )
    
    integrator = result[2]
    
    # Create a simple context
    context = openmm.Context(system, integrator)
    context.setPositions(positions)
    
    # Test the scenario: run integration steps to trigger edge cases
    print("Testing GaMD boost calculations for NaN stability...")
    
    for i in range(250):  # Run sufficient steps to trigger all edge cases
        integrator.step(1)
        
        # Check for NaN values in key variables
        sigmaV = integrator.getGlobalVariableByName('sigmaV_Total')
        k0 = integrator.getGlobalVariableByName('k0_Total')
        k0prime = integrator.getGlobalVariableByName('k0prime_Total')
        
        # Check if any values are NaN
        assert str(sigmaV) != 'nan', f"NaN detected in sigmaV at step {i}"
        assert str(k0) != 'nan', f"NaN detected in k0 at step {i}"
        assert str(k0prime) != 'nan', f"NaN detected in k0prime at step {i}"
    
    print("SUCCESS: No NaN values detected during integration!")
    
    # Final validation of all key variables
    sigmaV = integrator.getGlobalVariableByName('sigmaV_Total')
    k0 = integrator.getGlobalVariableByName('k0_Total')
    k0prime = integrator.getGlobalVariableByName('k0prime_Total')
    windowCount = integrator.getGlobalVariableByName('windowCount')
    
    print(f"Final values:")
    print(f"  windowCount: {windowCount}")
    print(f"  sigmaV_Total: {sigmaV}")
    print(f"  k0_Total: {k0}")
    print(f"  k0prime_Total: {k0prime}")

if __name__ == "__main__":
    test_nan_fix()
    print("\nTest PASSED: NaN bug fix is working correctly!")
