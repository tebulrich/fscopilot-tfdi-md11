# TFDi Design MD-11 FS Copilot Configuration

FS Copilot configuration files for the TFDi Design MD-11 aircraft. This generator creates FS Copilot format YAML files using `get:`/`set:` syntax.

## Table of Contents

- [Overview](#overview)
- [Status](#status)
- [Documentation References](#documentation-references)
- [Project Structure](#project-structure)
- [Quick Start](#quick-start)
- [Category System](#category-system)
- [Module Generator](#module-generator)
- [Workflow](#workflow)
- [File Locations](#file-locations)

## Overview

This project generates FS Copilot configuration files for the TFDi Design MD-11 aircraft. The generator creates YAML files in FS Copilot format, organized by cockpit system and panel location.

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

The `tfdi-md11-data/json/` folder contains JSON files for each panel/system category. The `validate.py` script checks coverage and marks implemented events.

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

# Regenerate all categories as modular files grouped by cockpit system
python generate.py --split-grouped

# Generate a single category as separate module file
python generate.py <category_name> --split

# Specify custom output path for aircraft file
python generate.py --output-path C:\Path\To\FS\Copilot\Definitions
```

### What It Does

The generator reads category JSON files, groups events by control type, detects L: variables, and generates FS Copilot format YAML files with appropriate `get:`/`set:` syntax.

### Features

- Handles button DOWN/UP pairs automatically
- Groups wheel events (WHEEL_UP/WHEEL_DOWN)
- Handles switches with LEFT/RIGHT buttons
- Handles ground buttons (GRD_LEFT_BUTTON_DOWN)
- Handles push/pull buttons (PUSH_UP/DOWN, PULL_UP/DOWN) from XML metadata
- Automatically syncs L: variables when available
- Automatically generates event triggers with appropriate prefixes (>B: for custom TFDi events, >K: for standard MSFS events)
- Generates appropriate comments for each control group
- Creates standard headers with references to documentation
- Supports property overrides via object format in JSON files
- Integrates XML metadata for improved comment generation and type detection
- Supports modular output with system grouping

### Output Modes

The generator supports three output modes:

1. **Consolidated Mode (Default)**: All categories are consolidated into a single `TFDi_Design_MD-11.yaml` file.

2. **Modular Mode - Individual Categories (`--split`)**: Generates one module file per category (e.g., `TFDi_MD11_glareshield_left.yaml`, `TFDi_MD11_overhead_panel.yaml`).

3. **Modular Mode - System Grouping (`--split-grouped`)**: Organizes related categories by cockpit system and panel location into grouped module files:
   - **Glareshield**: glareshield_left, glareshield_right, center_glareshield
   - **Overhead**: overhead_panel, aft_overhead_panel
   - **Pedestal**: pedestal, radio_panel, audio_panel, throttle
   - **Instruments**: main_instruments_panel, left_side_panel, right_side_panel, center_panel, left_ecp, right_ecp
   - **Flight Controls**: flight_controls, left_yoke, right_yoke
   - **FMC**: fmc_cdu


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

You can use an object format to specify overrides:

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

- `--split`: Creates separate module files in `Definitions/modules/tfdi-md11/` instead of merging into the main aircraft file
- `--split-grouped`: Creates grouped module files organized by cockpit system and panel location
- `--output-path` or `--output`: Specifies a custom directory path for the output aircraft YAML file. Overrides the path specified in `config.json`

### Configuration File

You can create a `config.json` file in the project root to set default values:

```json
{
  "output_path": "C:\\Users\\YourName\\AppData\\Local\\Packages\\Microsoft.FlightSimulator_8wekyb3d8bbwe\\LocalCache\\Packages\\Community\\FsCopilot\\Definitions"
}
```

The `output_path` setting will be used automatically if no `--output-path` argument is provided. Command-line arguments always override the config file.

## Workflow

Regenerate all categories:
```bash
python generate.py
```

Regenerate a specific category:
```bash
python generate.py <category_name>
```

Generate with separate module files:
```bash
python generate.py --split
python generate.py --split-grouped
```

Verify coverage:
```bash
python validate.py
python validate.py <category_name>
```

## Important Notes

- The generator automatically detects L: variables and uses them when available, otherwise generates event triggers
- Event prefixes follow patterns: `OBS_` for Observer, `PED_CPT_` and `PED_FO_` for Captain/First Officer
- The `validate.py` script marks events as "// present" in JSON files to track coverage

## File Locations

- Main aircraft config: `Definitions/TFDi_Design_MD-11.yaml` (or custom path from `config.json`)
- Module files (non-merged): `Definitions/modules/tfdi-md11/TFDi_MD11_*.yaml`
- Category files: `tfdi-md11-data/json/*.json`
- Variables file: `tfdi-md11-data/json/variables.json`
- XML files: `tfdi-md11-data/xml/*.xml` (used for metadata extraction)
- Configuration file: `config.json` (optional)
- Validation script: `validate.py`
- Generator script: `generate.py`

## Grouping Logic

The generator handles event patterns automatically:
- Buttons (_BT) and switches (_SW) are grouped separately
- Brightness wheel events (_BRT_KB_WHEEL) extract the full prefix
- Ground buttons (_GRD_LEFT_BUTTON_DOWN) are preserved as separate controls
- Switch RIGHT buttons are grouped with their corresponding LEFT buttons
- L: variables are detected from `variables.json` (1477 variables) to determine control types
- XML metadata (TOOLTIPID, NUM_STATES, etc.) is used for improved comment generation and type detection
