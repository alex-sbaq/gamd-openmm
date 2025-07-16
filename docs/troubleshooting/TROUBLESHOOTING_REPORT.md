# GaMD Simulation Stage Transition Issue - Analysis and Solution

## Problem Description
The GaMD simulation was not transitioning from conventional MD to GaMD phases due to invalid stage boundaries caused by incorrect interpretation of the step configuration in the input XML file.

## Root Cause Analysis

### Issue: Invalid Stage Boundaries
The original `input.xml` had the following configuration:
```xml
<number-of-steps>
    <conventional-md-prep>200000</conventional-md-prep>
    <conventional-md>200000</conventional-md>
    <gamd-equilibration-prep>200000</gamd-equilibration-prep>
    <gamd-equilibration>200000</gamd-equilibration>
    <gamd-production>50000000</gamd-production>
    <averaging-window-interval>500</averaging-window-interval>
</number-of-steps>
```

### Understanding the Step Configuration Format
The XML configuration has a **mixed format**:
- `<conventional-md-prep>`: Individual stage length (200000 steps)
- `<conventional-md>`: **CUMULATIVE** total including prep (should be 400000 for 200k prep + 200k actual)
- `<gamd-equilibration-prep>`: Individual stage length (200000 steps)  
- `<gamd-equilibration>`: **CUMULATIVE** total including prep (should be 400000 for 200k prep + 200k actual)
- `<gamd-production>`: Individual stage length (50000000 steps)

The issue was that `<conventional-md>` and `<gamd-equilibration>` were set to the same values as their prep stages, creating invalid stage boundaries where the end step equals the start step.

This created the following stage boundaries:
- Stage 1 (Conv MD Prep): 0 to 200000 ✓
- Stage 2 (Conv MD): 200001 to 200000 ❌ (End < Start!)
- Stage 3 (GaMD Eq Prep): 200001 to 400000 ✓
- Stage 4 (GaMD Eq): 400001 to 400000 ❌ (End < Start!)
- Stage 5 (GaMD Prod): 400001 to 50400000 ✓

### Technical Details
The `GamdStageIntegrator` class in `gamd/stage_integrator.py` expects the following parameter meanings:

```python
# From the constructor documentation:
# ntcmdprep: The number of conventional MD steps for system equilibration.
# ntcmd:     The total number of conventional MD steps (including ntcmdprep)
# ntebprep:  The number of GaMD pre-equilibration steps.
# nteb:      The number of GaMD equilibration steps (including ntebprep)
# nstlim:    The total number of simulation steps.
```

The stage boundaries are calculated as:
```python
self.stage_1_start = 0
self.stage_1_end = ntcmdprep                    # Individual prep steps
self.stage_2_start = ntcmdprep + 1
self.stage_2_end = ntcmd                        # CUMULATIVE: prep + actual conventional MD
self.stage_3_start = ntcmd + 1
self.stage_3_end = ntcmd + ntebprep             # ntcmd + individual GaMD prep steps
self.stage_4_start = ntcmd + ntebprep + 1
self.stage_4_end = ntcmd + nteb                 # ntcmd + CUMULATIVE GaMD equilibration
self.stage_5_start = ntcmd + nteb + 1
self.stage_5_end = nstlim                       # Total simulation steps
```

## Solution

### Corrected XML Configuration
The XML should use the proper **mixed format** where some values are individual stage lengths and others are cumulative:

```xml
<number-of-steps>
    <conventional-md-prep>200000</conventional-md-prep>      <!-- Individual stage: 200k steps -->
    <conventional-md>400000</conventional-md>                <!-- CUMULATIVE: 200k prep + 200k actual -->
    <gamd-equilibration-prep>200000</gamd-equilibration-prep><!-- Individual stage: 200k steps -->
    <gamd-equilibration>400000</gamd-equilibration>          <!-- CUMULATIVE: 200k prep + 200k actual -->
    <gamd-production>50000000</gamd-production>              <!-- Individual stage: 50M steps -->
    <averaging-window-interval>500</averaging-window-interval>
</number-of-steps>
```

**Key Point**: The `gamd-equilibration-prep` value (200000) is NOT cumulative - it's the individual stage length. The `gamd-equilibration` value (400000) IS cumulative and includes the prep steps.

This creates valid stage boundaries:
- Stage 1 (Conv MD Prep): 0 to 200000
- Stage 2 (Conv MD): 200001 to 400000
- Stage 3 (GaMD Eq Prep): 400001 to 600000
- Stage 4 (GaMD Eq): 600001 to 800000
- Stage 5 (GaMD Prod): 800001 to 50800000

### Simulation Timeline
With the corrected configuration:
- **Steps 1-200000 (400 ps)**: Conventional MD preparation - system equilibration
- **Steps 200001-400000 (800 ps)**: Conventional MD - collect boost parameters (Vmax, Vmin, Vavg, sigmaV)
- **Steps 400001-600000 (1200 ps)**: GaMD pre-equilibration - apply boost with fixed parameters from Stage 2
- **Steps 600001-800000 (1600 ps)**: GaMD equilibration - apply boost with updated parameters
- **Steps 800001-50800000 (101600 ps)**: GaMD production - apply boost with fixed parameters from Stage 4

## Key Requirements

1. **Mixed Format Understanding**: 
   - `conventional-md-prep`: Individual stage length
   - `conventional-md`: **CUMULATIVE** (prep + actual conventional MD)
   - `gamd-equilibration-prep`: Individual stage length  
   - `gamd-equilibration`: **CUMULATIVE** (prep + actual GaMD equilibration)
   - `gamd-production`: Individual stage length

2. **Divisibility**: Both `conventional-md` and `gamd-equilibration` must be divisible by `averaging-window-interval`

3. **Proper Stage Ordering**: Each stage end must be greater than the previous stage start

4. **Cumulative Values Must Be Greater Than Prep Values**:
   - `conventional-md` > `conventional-md-prep`
   - `gamd-equilibration` > `gamd-equilibration-prep`

## Files Modified
- Created `corrected_input.xml` with the proper cumulative step configuration
- **Added validation checks** to prevent this issue in the future:
  - Enhanced `GamdStageIntegrator` constructor with `_validate_stage_configuration()` method
  - Added `validate_step_configuration()` method to `IntegratorNumberOfStepsConfig` class
  - Modified XML parser to automatically validate configuration after parsing

## Validation Checks Added

### Configuration-Level Validation
The XML parser now automatically validates the step configuration when parsing input files. Invalid configurations will be caught immediately with helpful error messages.

### Integrator-Level Validation
The GaMD integrator constructor now performs comprehensive validation of stage boundaries before simulation begins.

### Common Errors Detected
1. **Cumulative values not greater than prep values**: Catches when `conventional-md` <= `conventional-md-prep` or `gamd-equilibration` <= `gamd-equilibration-prep`
2. **Invalid stage boundaries**: Detects when stage end steps are less than start steps
3. **Divisibility requirements**: Ensures `conventional-md` and `gamd-equilibration` are divisible by `averaging-window-interval`
4. **Minimum value checks**: Validates that all step counts are positive
5. **Averaging window requirements**: Ensures cumulative values are at least as large as the averaging window

### Error Messages
The validation provides clear, actionable error messages with:
- Specific parameter values that are problematic
- Explanation of the cumulative vs individual format
- Example of correct configuration
- Calculated stage boundaries showing the problem

## Verification
The corrected configuration was tested and shows proper stage transitions with valid boundaries.

## Summary: Which Values Are Cumulative vs Individual

**CRITICAL CLARIFICATION**: The `<number-of-steps>` configuration uses a **mixed format**:

### Individual Stage Lengths (NOT cumulative):
- `<conventional-md-prep>` = Number of prep steps only
- `<gamd-equilibration-prep>` = Number of GaMD prep steps only  
- `<gamd-production>` = Number of production steps only

### Cumulative Totals (INCLUDING prep):
- `<conventional-md>` = Total conventional MD steps (prep + actual)
- `<gamd-equilibration>` = Total GaMD equilibration steps (prep + actual)

### Example:
If you want 200k prep + 200k actual for each phase:
```xml
<conventional-md-prep>200000</conventional-md-prep>     <!-- 200k prep steps -->
<conventional-md>400000</conventional-md>               <!-- 200k prep + 200k actual = 400k total -->
<gamd-equilibration-prep>200000</gamd-equilibration-prep><!-- 200k prep steps -->
<gamd-equilibration>400000</gamd-equilibration>         <!-- 200k prep + 200k actual = 400k total -->
```

**The key insight**: `gamd-equilibration-prep` equals `conventional-md-prep` in your case because you want the same prep duration for both phases, but the cumulative values must be larger than their prep counterparts.
