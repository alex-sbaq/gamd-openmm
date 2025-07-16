# GaMD Validation System Implementation

## Overview
Added comprehensive validation checks to the GaMD codebase to prevent stage transition issues caused by invalid step configurations.

## Validation Levels

### 1. Configuration-Level Validation
**Location**: `gamd/config.py` - `IntegratorNumberOfStepsConfig.validate_step_configuration()`

**When**: Called automatically during XML parsing

**Checks**:
- Cumulative values > prep values
- Divisibility by averaging window interval
- Minimum positive values
- Proper averaging window sizing

### 2. XML Parser Validation
**Location**: `gamd/parser.py` - `XmlParser.parse_file()`

**When**: Called automatically after parsing XML configuration

**Purpose**: Catches configuration errors before simulation setup

### 3. Integrator-Level Validation
**Location**: `gamd/stage_integrator.py` - `GamdStageIntegrator._validate_stage_configuration()`

**When**: Called during integrator construction

**Checks**:
- All configuration-level checks
- Stage boundary calculations
- Detailed stage transition validation

## Error Messages
All validation levels provide:
- Clear identification of problematic parameters
- Explanation of cumulative vs individual format
- Example of correct configuration
- Calculated stage boundaries showing the issue

## Usage Examples

### Valid Configuration
```xml
<number-of-steps>
    <conventional-md-prep>200000</conventional-md-prep>      <!-- Individual: 200k steps -->
    <conventional-md>400000</conventional-md>                <!-- Cumulative: 200k + 200k -->
    <gamd-equilibration-prep>200000</gamd-equilibration-prep><!-- Individual: 200k steps -->
    <gamd-equilibration>400000</gamd-equilibration>          <!-- Cumulative: 200k + 200k -->
    <gamd-production>50000000</gamd-production>              <!-- Individual: 50M steps -->
    <averaging-window-interval>500</averaging-window-interval>
</number-of-steps>
```

### Invalid Configuration (Caught by Validation)
```xml
<number-of-steps>
    <conventional-md-prep>200000</conventional-md-prep>
    <conventional-md>200000</conventional-md>                <!-- ERROR: Same as prep -->
    <gamd-equilibration-prep>200000</gamd-equilibration-prep>
    <gamd-equilibration>200000</gamd-equilibration>          <!-- ERROR: Same as prep -->
    <gamd-production>50000000</gamd-production>
    <averaging-window-interval>500</averaging-window-interval>
</number-of-steps>
```

## Benefits
1. **Early Error Detection**: Catches configuration errors before simulation starts
2. **Clear Error Messages**: Provides actionable feedback to users
3. **Prevents Silent Failures**: Eliminates stage transition issues
4. **Educational**: Error messages teach users the correct format
5. **Comprehensive**: Validates all aspects of step configuration

## Files Modified
- `gamd/stage_integrator.py`: Added `_validate_stage_configuration()` method
- `gamd/config.py`: Added `validate_step_configuration()` method
- `gamd/parser.py`: Added automatic validation call after parsing

## Testing
Comprehensive test suite validates:
- Configuration-level validation
- XML parsing validation
- Integrator-level validation
- Valid configurations pass all checks
- Invalid configurations are properly caught

The validation system ensures that the original issue (stage transition failure due to invalid stage boundaries) can never occur again.
