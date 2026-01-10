# TFDi Design MD-11 FS Copilot Configuration

FS Copilot configuration files for the TFDi Design MD-11 aircraft. This generator creates FS Copilot format YAML files that use `get:`/`set:` syntax and bypass the CEVENT limitation by supporting direct L: variable writes and >B: events (H-events).

## Table of Contents

- [Overview](#overview)
- [Status](#status)
- [Documentation References](#documentation-references)
- [Project Structure](#project-structure)
- [Quick Start](#quick-start)
- [Category System](#category-system)
- [Module Generator](#module-generator)
- [FS Copilot Format](#fs-copilot-format)
- [CEVENT Limitation Bypass](#cevent-limitation-bypass)
- [Workflow](#workflow)
- [File Locations](#file-locations)

## Overview

This project generates comprehensive FS Copilot configuration files for the TFDi Design MD-11 aircraft. FS Copilot is a shared cockpit add-on for MSFS 2024 that uses a YAML-based configuration with JavaScript logic. Unlike YourControls, FS Copilot supports direct L: variable writes and >B: events, which completely bypass the CEVENT limitation where only one discrete value can be processed at a time.

The configuration is organized into modular YAML files, with each module covering a specific panel/system. All events are consolidated into a single main aircraft configuration file.

## Status

1423 events across 19 categories are supported by the generator.

### Completed Modules

1. Audio Panel - Audio panel controls (Captain, First Officer, Observer)
2. Radio Panel - Radio panel controls
3. FMC/CDU - FMC/CDU button events (LMCDU, RMCDU, CDU, CMCDU)
4. Aft Overhead Panel - Aft overhead panel (APU, Fire, Cargo Smoke, GPWS, Evacuation)
5. Overhead Panel - Main overhead panel
6. Center Glareshield - Center glareshield / Autopilot Control Panel
7. Glareshield Left - Left glareshield
8. Glareshield Right - Right glareshield
9. Center Panel - Center panel
10. Pedestal - Pedestal controls
11. Left Side Panel - Left side panel
12. Right Side Panel - Right side panel
13. Left ECP - Left ECP
14. Right ECP - Right ECP
15. Left Yoke - Left yoke controls
16. Right Yoke - Right yoke controls
17. Flight Controls - Flight controls
18. Throttle - Throttle controls
19. Main Instruments Panel - Main instruments panel

All events are consolidated in: `Definitions/TFDi_Design_MD-11.yaml`

## Documentation References

- [Events Documentation](https://docs.tfdidesign.com/md11/integration-guide/events)
- [Variables Documentation](https://docs.tfdidesign.com/md11/integration-guide/variables)
- [FS Copilot Wiki](https://github.com/yury-sch/FsCopilot/wiki) - Complete guide to FS Copilot definitions format

## Project Structure

```
fscopilot-tfdi-md11/
├── Definitions/
│   ├── TFDi_Design_MD-11.yaml          # Main aircraft configuration (FS Copilot format)
│   └── modules/
│       ├── tfdi-md11/                   # TFDi MD-11 modules (when using --split)
│       │   └── TFDi_MD11_*.yaml
│       └── *.yaml                       # Standard FS Copilot modules
├── tfdi-md11-data/
│   ├── json/
│   │   ├── *.json                       # Category definition files
│   │   └── variables.json               # L: variable definitions
│   └── xml/
│       └── *.xml                        # XML definition files (for metadata)
├── config.json                          # Configuration file (optional)
├── generate.py                          # Module generator script
├── validate.py                          # Coverage verification script
└── README.md                           # This file
```

## Quick Start

### Installation

1. Install FS Copilot (MSFS 2024 shared cockpit add-on)
2. Clone this repository
3. Install Python dependencies:
   ```bash
   pip install pyyaml
   ```

### Generate Configuration

Generate all categories into the main aircraft file:
```bash
python generate.py
```

Generate a specific category:
```bash
python generate.py audio_panel
```

Specify custom output path (FS Copilot Definitions folder):
```bash
python generate.py --output-path C:\Users\YourName\AppData\Local\Packages\Microsoft.FlightSimulator_8wekyb3d8bbwe\LocalCache\Packages\Community\FsCopilot\Definitions
```

### Verify Coverage

Check coverage for a specific category:
```bash
python validate.py <category_name>
```

Check all categories:
```bash
python validate.py
```

## Category System

The `tfdi-md11-data/json/` folder contains JSON files for each panel/system category. Each JSON file lists all events from the documentation that should be implemented for that category.

The `validate.py` script:
- Searches for each event in the main aircraft YAML file
- Marks events as "// present" in the JSON file if found
- Reports coverage percentage

## Module Generator

The Python script (`generate.py`) automatically generates FS Copilot format YAML files from category JSON files.

### Usage

```bash
# Regenerate all categories (merges into main aircraft file by default)
python generate.py

# Generate a single category (merges into main aircraft file)
python generate.py <category_name>

# Regenerate all categories as separate module files (one file per category)
python generate.py --split

# Regenerate all categories as modular files grouped by cockpit system (recommended for large configs)
python generate.py --split-grouped

# Generate a single category as separate module file
python generate.py <category_name> --split

# Specify custom output path for aircraft file
python generate.py --output-path C:\Path\To\FS\Copilot\Definitions
```

### What It Does

1. Reads the category JSON file (`tfdi-md11-data/json/<category_name>.json`)
2. Extracts all events (automatically filters out "// present" markers)
3. Groups events by control type (buttons, wheels, switches, etc.)
4. Detects L: variables from `tfdi-md11-data/json/variables.json` to determine control types
5. Generates FS Copilot format YAML with `get:`/`set:` syntax
6. Marks all implemented events as "// present" in the JSON category file

### Features

- Handles button DOWN/UP pairs automatically
- Groups wheel events (WHEEL_UP/WHEEL_DOWN)
- Handles switches with LEFT/RIGHT buttons
- Handles ground buttons (GRD_LEFT_BUTTON_DOWN)
- Handles push/pull buttons (PUSH_UP/DOWN, PULL_UP/DOWN) from XML metadata
- Automatically syncs L: variables for state synchronization (bypasses CEVENT)
- Automatically generates event triggers with >B: for custom TFDi events (bypasses CEVENT)
- Uses >K: for standard MSFS events
- Generates appropriate comments for each control group
- Creates standard headers with references to documentation
- Supports property overrides via object format in JSON files
- Integrates XML metadata for improved comment generation and type detection
- Supports modular output with system grouping for better maintainability of large configurations

### Output Modes

The generator supports three output modes:

1. **Consolidated Mode (Default)**: All categories are consolidated into a single `TFDi_Design_MD-11.yaml` file. Suitable for smaller configurations or when a unified file structure is preferred.

2. **Modular Mode - Individual Categories (`--split`)**: Generates one module file per category (e.g., `TFDi_MD11_glareshield_left.yaml`, `TFDi_MD11_overhead_panel.yaml`). Results in multiple smaller, category-specific files.

3. **Modular Mode - System Grouping (`--split-grouped`)**: Organizes related categories by cockpit system functionality and panel location into logically grouped module files:
   - **Glareshield**: glareshield_left, glareshield_right, center_glareshield
   - **Overhead**: overhead_panel, aft_overhead_panel
   - **Pedestal**: pedestal, radio_panel, audio_panel, throttle
   - **Instruments**: main_instruments_panel, left_side_panel, right_side_panel, center_panel, left_ecp, right_ecp
   - **Flight Controls**: flight_controls, left_yoke, right_yoke
   - **FMC**: fmc_cdu

   System grouping mode is recommended for large aircraft configurations as it improves maintainability and organization while keeping related controls grouped by cockpit location. Ideal for configurations exceeding 2000 lines.

### XML Metadata Integration

The script extracts the following metadata from XML files to improve comment generation and control type detection:

- **TOOLTIPID**: Used for generating human-readable comments
- **NODE_ID**: Maps to L: variable names and event names
- **NUM_STATES**: Detects multi-state switches and controls
- **GUARD_ID**: Identifies controls with safety guards
- **LEFT_BUTTON_DOWN/UP, RIGHT_BUTTON_DOWN/UP**: Detects button controls
- **WHEEL_UP/DOWN**: Detects wheel/rotary controls
- **PULL_UP/DOWN, PUSH_UP/DOWN**: Detects push-pull controls (e.g., fire handles)

Note: VAR_NAME and ANIM_CODE fields are used for lighting/animation in the aircraft model and are not needed for control mapping.

### Event Overrides

The generator supports overriding YAML properties for individual events. While the default format uses simple strings:

```json
"events": [
  "CTR_ANTISKID_BT_LEFT_BUTTON_DOWN",
  "CTR_ANTISKID_BT_LEFT_BUTTON_UP"
]
```

You can use an object format to specify overrides (note: FS Copilot format may have different override options):

```json
"events": [
  "CTR_ANTISKID_BT_LEFT_BUTTON_DOWN",
  {
    "event": "CTR_AUX_HYD_PUMP_BT_LEFT_BUTTON_DOWN",
    "increment_by": 2
  }
]
```

The generator will automatically apply these overrides to the generated YAML entries. Both formats can be mixed in the same JSON file.

### Flags

- `--split`: Creates separate module files in `Definitions/modules/tfdi-md11/` instead of merging into the main aircraft file. The aircraft file will include references to these modules. Works with both all categories and single category. By default (without `--split`), all events are merged directly into the main aircraft YAML file.

- `--output-path` or `--output`: Specifies a custom directory path for the output aircraft YAML file. The path can include or omit a trailing slash. The output file will be named `TFDi_Design_MD-11.yaml` in the specified directory. If the directory doesn't exist, it will be created automatically. This overrides the path specified in `config.json`.

### Configuration File

You can create a `config.json` file in the project root to set default values:

```json
{
  "output_path": "C:\\Users\\YourName\\AppData\\Local\\Packages\\Microsoft.FlightSimulator_8wekyb3d8bbwe\\LocalCache\\Packages\\Community\\FsCopilot\\Definitions"
}
```

The `output_path` setting will be used automatically if no `--output-path` argument is provided. Command-line arguments always override the config file.

### Behavior

- Running without arguments (`python generate.py`): Regenerates all categories and merges into main aircraft file
- Running with a category name (`python generate.py center_panel`): Regenerates only that category and merges into main aircraft file
- Running with `--split` flag (`python generate.py --split`): Regenerates all categories as separate module files
- Running with category and `--split` (`python generate.py center_panel --split`): Generates that category as a separate module file

### Deduplication

The generator automatically prevents duplicate entries when merging categories:

- **All categories mode**: Preserves manually-added entries (those without `L:MD11_` variables or generated event patterns) and replaces all generated entries with fresh content from categories
- **Single category mode**: Preserves manually-added entries and entries from other categories, but replaces entries from the category being regenerated to prevent duplicates
- Generated entries are identified by the presence of `L:MD11_` variables or event patterns like `_BT_LEFT_BUTTON`, `_KB_WHEEL`, `_SW_LEFT_BUTTON`, or `_GRD_LEFT_BUTTON`

This ensures that running the generator multiple times does not create duplicate entries in the output file.

## FS Copilot Format

FS Copilot uses a different YAML format than YourControls. Instead of `type:`, `var_name:`, `event_name:`, FS Copilot uses `get:` and `set:` syntax.

> 📚 **For complete documentation on FS Copilot format, see the [FS Copilot Wiki](https://github.com/yury-sch/FsCopilot/wiki)** - This guide explains all fields (`get:`, `set:`, `skp:`), JavaScript expressions, implicit rules, and more.

### Format Overview

FS Copilot format entries use:
- `get:` - Reads/syncs a variable (L: variable, A: variable, or H: event)
- `set:` - Executes when the `get:` variable changes, can contain JavaScript expressions or calculator code

### L: Variable Sync (State Synchronization)

For controls with L: variables, FS Copilot syncs the variable value directly, bypassing CEVENT entirely:

```yaml
  - # Control Name
    get: L:MD11_VARIABLE_NAME
```

When the master changes the L: variable value, it automatically syncs to all clients. The aircraft's internal logic reads the L: variable and reacts accordingly.

### Event Triggers

For controls without L: variables or for direct event triggering:

```yaml
  - # Control Name
    set: (>B:CUSTOM_TFDI_EVENT_NAME)
```

or for standard MSFS events:

```yaml
  - # Control Name
    set: (>K:STANDARD_MSFS_EVENT)
```

### Toggle Switches with L: Variables

For toggle switches with L: variables, FS Copilot syncs the variable directly:

```yaml
  - # Switch Name
    get: L:MD11_SWITCH_VAR
```

The variable value is synced automatically, and the aircraft's logic reacts to the L: variable change.

For single-event switches (NUM_STATES=1 from XML), events are triggered:

```yaml
  - # Single-Event Switch
    get: L:MD11_SWITCH_VAR
    set: (>B:SWITCH_EVENT_DOWN)
```

### Wheel Controls with L: Variables

For wheel controls with L: variables, the L: variable is synced directly:

```yaml
  - # Wheel Control Name
    get: L:MD11_WHEEL_VAR
```

The master's wheel action changes the L: variable value, which syncs to all clients, bypassing the need for event-based control and the CEVENT limitation.

### Wheel Controls without L: Variables

For wheel controls without L: variables, events are triggered directly:

```yaml
  - # Wheel Control Name (Wheel Up)
    set: (>B:WHEEL_UP_EVENT)
  
  - # Wheel Control Name (Wheel Down)
    set: (>B:WHEEL_DOWN_EVENT)
```

### Simple Event Triggers

For simple button presses or controls without state tracking:

```yaml
  - # Button Name
    set: (>B:EVENT_NAME)
```

## CEVENT Limitation Bypass

### The Problem

YourControls has a fundamental limitation: CEVENT values are sent on button presses, but only 1 discrete value may be output at a time. This means:

- When the Pilot Flying (PF) is hand-flying and using the elevator trim constantly, many MCDU entries by the Pilot Monitoring (PM) will be lost
- The CEVENT is capturing the trim commands and missing/ignoring the incoming MCDU commands
- Only 1 person should perform any action at a time to avoid conflicts

### The Solution

FS Copilot bypasses this limitation in two ways:

1. **Direct L: Variable Writes**: FS Copilot can sync L: variable values directly (`get: L:MD11_VAR`). When the master changes the L: variable, it syncs to all clients, and the aircraft's internal logic reads it. This completely bypasses CEVENT.

2. **>B: Events (H-events)**: FS Copilot uses >B: syntax for custom TFDi events (Behavior/H-events), which bypass CEVENT. Standard MSFS events use >K: syntax (Key events).

3. **>L: Direct Variable Writes**: FS Copilot supports direct L: variable writes using `>L:VAR_NAME` syntax in `set:` expressions, allowing direct state manipulation without events.

This means:
- Multiple pilots can interact with different systems simultaneously
- MCDU entries won't be lost while trim is being used
- State synchronization works reliably for all controls with L: variables
- Custom TFDi events are properly routed without CEVENT conflicts

## Workflow

### Regenerating the Configuration

To regenerate the entire configuration from scratch:

```bash
# Regenerate all categories and merge into main aircraft file
python generate.py

# Verify coverage
python validate.py
```

### Updating a Single Category

To regenerate a specific category:

```bash
# Regenerate a single category
python generate.py <category_name>

# Verify coverage for that category
python validate.py <category_name>
```

### Working with Separate Module Files

If you prefer to work with separate module files instead of a merged configuration:

```bash
# Generate all categories as separate module files
python generate.py --split

# Generate a single category as a separate module file
python generate.py <category_name> --split
```

The generator script automatically:
- Groups related events together
- Detects appropriate control types (L: variable sync vs event triggers)
- Formats YAML with proper indentation and comments
- Updates category files to mark events as present

### Verification

After generating or modifying the configuration, always verify coverage:

```bash
# Check all categories
python validate.py

# Check a specific category
python validate.py <category_name>
```

## Important Notes

1. **Event Prefixes**: Event prefixes follow specific patterns: Observer events use `OBS_` prefix, Captain/First Officer events use `PED_CPT_` and `PED_FO_` prefixes.

2. **Control Types**: Some controls have both button events (`_BT_LEFT_BUTTON_DOWN/UP`) and wheel events (`_KB_WHEEL_UP/DOWN`).

3. **L: Variables**: Not all events have corresponding L: variables - the generator automatically uses event triggers when no variable exists.

4. **Validation**: The `validate.py` script marks events as "// present" in JSON files - this is expected behavior and helps track coverage.

5. **YAML Syntax**: YAML syntax requires strict indentation (2 spaces) - the generator handles this automatically.

6. **FS Copilot Compatibility**: This generator creates FS Copilot format files. FS Copilot is for MSFS 2024 only. The format is not compatible with YourControls.

7. **CEVENT Bypass**: Controls with L: variables use direct variable sync, which completely bypasses CEVENT. Controls without L: variables use >B: events for custom TFDi events (bypasses CEVENT) or >K: events for standard MSFS events.

## File Locations

- Main aircraft config: `Definitions/TFDi_Design_MD-11.yaml` (or custom path from `config.json`)
- Module files (non-merged): `Definitions/modules/tfdi-md11/TFDi_MD11_*.yaml`
- Category files: `tfdi-md11-data/json/*.json`
- Variables file: `tfdi-md11-data/json/variables.json`
- XML files: `tfdi-md11-data/xml/*.xml` (used for metadata extraction)
- Configuration file: `config.json` (optional, for default output path)
- Validation script: `validate.py`
- Generator script: `generate.py`

## Grouping Logic

The grouping logic in `generate.py` has been carefully refined to handle all event patterns:

1. **Control Type Distinction**: Buttons (_BT) and switches (_SW) are grouped separately even if they share the same base name
2. **Brightness Wheel Events**: _BRT_KB_WHEEL events extract the full prefix (e.g., PED_DU1_BRT_KB)
3. **Ground Button Events**: _GRD_LEFT_BUTTON_DOWN events are preserved as separate controls with _GRD suffix
4. **Switch RIGHT Buttons**: _SW_RIGHT_BUTTON_DOWN events are grouped with their corresponding _SW_LEFT_BUTTON_DOWN control
5. **L: Variable Detection**: The script loads variables from `tfdi-md11-data/json/variables.json` (1477 variables) and automatically detects which controls should use L: variable sync vs event triggers
6. **XML Metadata Integration**: XML files provide tooltip information for better comment generation and NUM_STATES information for correct type detection (single-event switches vs toggle switches)

These features ensure that all events are correctly grouped, generated, and detected, achieving complete coverage across all categories.
