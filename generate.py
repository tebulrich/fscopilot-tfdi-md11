#!/usr/bin/env python3
"""
Generate FS Copilot YAML definition files from category JSON files.

This generator creates FS Copilot format YAML files (.yaml) that use get:/set: syntax
instead of YourControls format. FS Copilot supports direct L: variable writes and
>B: events (H-events), which bypass the CEVENT limitation.

Usage:
    python3 generate.py [category_name] [--split] [--split-grouped] [--output-path PATH]
    
Example:
    python3 generate.py                    # Regenerate all categories (merged)
    python3 generate.py center_panel        # Regenerate only center_panel (merged)
    python3 generate.py --split            # Regenerate all as individual module files (one per category)
    python3 generate.py --split-grouped    # Regenerate all as modular files grouped by cockpit system
    python3 generate.py center_panel --split  # Generate center_panel as separate module file
    python3 generate.py --output-path C:\\Users\\YourName\\Downloads\\FsCopilot_1.0-rc2\\Definitions
    
By default, all events are merged directly into the main aircraft YAML file.
This will read tfdi-md11-data/json/<category_name>.json and merge into 
Definitions/TFDi_Design_MD-11.yaml (FS Copilot format)

With --split flag, it will create separate module files in Definitions/modules/tfdi-md11/ 
instead of merging into the main aircraft file. Works with both all categories and single category.

With --output-path, you can specify a custom directory for the output aircraft YAML file.
The path can have or omit a trailing slash. Default is Definitions/ folder in project root.

Output Format:
    - Uses FS Copilot format: get:/set: syntax instead of type:/var_name:/event_name:
    - For L: variables: get: L:MD11_VAR (syncs state directly, bypasses CEVENT)
    - For events: set: "(>B:EVENT)" for custom TFDi events (bypasses CEVENT) or "(>K:EVENT)" for standard MSFS events
    - Supports JavaScript expressions in set: for conditional logic
"""

import json
import re
import sys
import xml.etree.ElementTree as ET
import yaml
from pathlib import Path

def load_xml_control_data():
    """Load comprehensive control data from XML files.
    
    Returns:
        Dictionary with:
        - 'tooltips': NODE_ID -> TOOLTIPID mapping
        - 'controls': NODE_ID -> control metadata (template_type, num_states, has_guard, events)
    """
    script_dir = Path(__file__).parent
    xml_dir = script_dir / "tfdi-md11-data" / "xml"
    
    if not xml_dir.exists():
        return {'tooltips': {}, 'controls': {}}
    
    tooltip_map = {}
    control_map = {}
    
    for xml_file in xml_dir.glob("*.xml"):
        try:
            tree = ET.parse(xml_file)
            root = tree.getroot()
            
            # Find all UseTemplate elements
            for template in root.findall(".//UseTemplate"):
                node_id_elem = template.find("NODE_ID")
                tooltip_elem = template.find("TOOLTIPID")
                template_name_attr = template.get("Name", "")
                
                if node_id_elem is not None:
                    node_id = node_id_elem.text
                    if not node_id:
                        continue
                    
                    # Remove MD11_ prefix if present
                    if node_id.startswith("MD11_"):
                        node_id_base = node_id[5:]  # Remove "MD11_"
                    else:
                        node_id_base = node_id
                    
                    # Extract tooltip
                    if tooltip_elem is not None and tooltip_elem.text:
                        tooltip = tooltip_elem.text
                        # Clean up tooltip: remove dynamic parts
                        clean_tooltip = re.sub(r'\s*\(.*?\).*$', '', tooltip)
                        clean_tooltip = clean_tooltip.strip()
                        if node_id_base not in tooltip_map:
                            tooltip_map[node_id_base] = clean_tooltip
                    
                    # Extract control metadata
                    control_info = {
                        'template_type': template_name_attr,
                        'num_states': None,
                        'has_guard': False,
                        'has_left_button': False,
                        'has_right_button': False,
                        'has_wheel': False,
                        'has_pull': False,
                        'has_push': False,
                        'guard_id': None
                    }
                    
                    # Check for NUM_STATES
                    num_states_elem = template.find("NUM_STATES")
                    if num_states_elem is not None and num_states_elem.text:
                        try:
                            control_info['num_states'] = int(num_states_elem.text)
                        except ValueError:
                            pass
                    
                    # Check for GUARD_ID
                    guard_id_elem = template.find("GUARD_ID")
                    if guard_id_elem is not None and guard_id_elem.text:
                        control_info['has_guard'] = True
                        guard_id = guard_id_elem.text
                        if guard_id.startswith("MD11_"):
                            control_info['guard_id'] = guard_id[5:]
                        else:
                            control_info['guard_id'] = guard_id
                    
                    # Check for event types
                    if template.find("LEFT_BUTTON_DOWN") is not None or template.find("LEFT_BUTTON_UP") is not None:
                        control_info['has_left_button'] = True
                    if template.find("RIGHT_BUTTON_DOWN") is not None or template.find("RIGHT_BUTTON_UP") is not None:
                        control_info['has_right_button'] = True
                    if template.find("WHEEL_UP") is not None or template.find("WHEEL_DOWN") is not None:
                        control_info['has_wheel'] = True
                    if template.find("PULL_UP") is not None or template.find("PULL_DOWN") is not None:
                        control_info['has_pull'] = True
                    if template.find("PUSH_UP") is not None or template.find("PUSH_DOWN") is not None:
                        control_info['has_push'] = True
                    
                    # Store control info
                    if node_id_base not in control_map:
                        control_map[node_id_base] = control_info
        except Exception as e:
            # Silently skip XML files that can't be parsed
            continue
    
    return {'tooltips': tooltip_map, 'controls': control_map}

# Cache XML data globally
_xml_data_cache = None

def get_xml_data():
    """Get cached XML data, loading if necessary."""
    global _xml_data_cache
    if _xml_data_cache is None:
        _xml_data_cache = load_xml_control_data()
    return _xml_data_cache

def get_xml_tooltips():
    """Get cached XML tooltips, loading if necessary."""
    return get_xml_data()['tooltips']

def get_xml_controls():
    """Get cached XML control metadata, loading if necessary."""
    return get_xml_data()['controls']

def format_comment_name(event_name):
    """Extract and format a readable name for comments from event name.
    
    First tries to match against XML TOOLTIPID values, then falls back to parsing.
    """
    tooltips = get_xml_tooltips()
    
    # Try to find matching NODE_ID base from XML
    # Event names like "OBS_AUDIO_PNL_VHF1_MIC_BT_LEFT_BUTTON_DOWN"
    # Should match NODE_ID base "OBS_AUDIO_PNL_VHF1_MIC_BT"
    
    # Extract potential base names by removing event suffixes
    suffixes = [
        '_LEFT_BUTTON_DOWN', '_LEFT_BUTTON_UP',
        '_RIGHT_BUTTON_DOWN', '_RIGHT_BUTTON_UP',
        '_WHEEL_UP', '_WHEEL_DOWN',
        '_PULL_DOWN', '_PULL_UP',
        '_PUSH_DOWN', '_PUSH_UP',
        '_GRD_LEFT_BUTTON_DOWN', '_GRD_LEFT_BUTTON_UP',
    ]
    
    for suffix in suffixes:
        if event_name.endswith(suffix):
            base = event_name[:-len(suffix)]
            if base in tooltips:
                return tooltips[base]
    
    # Also try direct match (for cases where event name = NODE_ID base)
    if event_name in tooltips:
        return tooltips[event_name]
    
    # Fallback to original parsing logic
    patterns = [
        (r'.*_BRT_KB_WHEEL', 'BRT Wheel Controls'),
        (r'.*_KB_WHEEL_(UP|DOWN)', 'Wheel Controls'),
        (r'.*_LSK_(\d+)(L|R)', lambda m: f'Line Select Key {m.group(1)}{m.group(2)}'),
        (r'.*_DIR_INTC', 'DIR'),
        (r'.*_ENG_OUT', 'ENG'),
        (r'.*_SEC_FPLN', 'SEC'),
        (r'.*_NAV_RAD', 'NAV'),
        (r'.*_PULL_BT', 'Pull Button'),
        (r'.*_PUSH_BT', 'Push Button'),
        (r'.*_GRD_LEFT_BUTTON', 'Ground Button'),
        (r'.*_SW_(LEFT|RIGHT)_BUTTON', 'Switch'),
        (r'.*_BT_LEFT_BUTTON_(DOWN|UP)', 'Button'),
    ]
    
    # Extract base name before event type
    base_match = re.match(r'[^_]+_(.+?)_(BT|SW|KB|GRD)_', event_name)
    if base_match:
        base = base_match.group(1)
        # Format the base name
        base = base.replace('_', ' ')
        return base.title()
    
    # Fallback: just use the event name
    return event_name

def load_config():
    """Load configuration from config.json file.
    
    Returns:
        Dictionary with configuration values, or empty dict if file doesn't exist
    """
    script_dir = Path(__file__).parent
    config_file = script_dir / "config.json"
    
    if config_file.exists():
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Could not load config.json: {e}", file=sys.stderr)
            return {}
    return {}

def get_aircraft_file_path(custom_output_path=None):
    """Get the path to the aircraft YAML file (FS Copilot format).
    
    Args:
        custom_output_path: Optional custom output directory path (overrides config)
    
    Returns:
        Path object to the aircraft YAML file
    """
    script_dir = Path(__file__).parent
    aircraft_filename = "TFDi_Design_MD-11.yaml"
    
    # Use command-line argument if provided, otherwise check config file
    output_path = custom_output_path
    if not output_path:
        config = load_config()
        output_path = config.get('output_path')
    
    if output_path:
        # Handle both with and without trailing slash
        output_path = Path(str(output_path).rstrip('/\\'))
        return output_path / aircraft_filename
    else:
        # Default location: FS Copilot uses Definitions/ folder
        return script_dir / "Definitions" / aircraft_filename

def load_variables():
    """Load L: variables from variables.json file."""
    script_dir = Path(__file__).parent
    data_dir = script_dir / "tfdi-md11-data" / "json"
    variables_file = data_dir / "variables.json"
    
    if not variables_file.exists():
        print(f"Warning: variables.json not found at {variables_file}", file=sys.stderr)
        return set()
    
    with open(variables_file) as f:
        data = json.load(f)
    
    variables = set(data.get('variables', []))
    print(f"Loaded {len(variables)} variables from variables.json")
    return variables

def find_l_variable(event_name, variables):
    """
    Find corresponding L: variable for an event.
    
    Mapping patterns:
    - PED_CPT_RADIO_PNL_VHF1_BT_LEFT_BUTTON_DOWN -> MD11_PED_CPT_RADIO_PNL_VHF1_BT
    - OBS_AUDIO_PNL_VHF1_MIC_BT_LEFT_BUTTON_DOWN -> MD11_OBS_AUDIO_PNL_VHF1_MIC_BT
    - PED_CPT_AUDIO_PNL_VHF1_MIC_BT_LEFT_BUTTON_DOWN -> MD11_PED_CPT_AUDIO_PNL_VHF1_MIC_BT
    """
    # Remove event suffixes to get base control name
    # Important: Keep _BT, _SW, etc. in the base name
    base = event_name
    
    # Remove button/switch event suffixes (but keep _BT, _SW prefixes)
    patterns_to_remove = [
        r'_LEFT_BUTTON_(DOWN|UP)$',      # Remove _LEFT_BUTTON_DOWN/UP
        r'_RIGHT_BUTTON_(DOWN|UP)$',     # Remove _RIGHT_BUTTON_DOWN/UP
        r'_GRD_LEFT_BUTTON_DOWN$',       # Remove _GRD_LEFT_BUTTON_DOWN
        r'_KB_WHEEL_(UP|DOWN)$',         # Remove _KB_WHEEL_UP/DOWN
        r'_WHEEL_(UP|DOWN)$',            # Remove _WHEEL_UP/DOWN
    ]
    
    for pattern in patterns_to_remove:
        base = re.sub(pattern, '', base)
    
    # Try to find matching variable
    # Pattern: MD11_<event_base>
    var_name = f"MD11_{base}"
    if var_name in variables:
        return f"L:{var_name}"
    
    return None

def parse_event_entry(entry):
    """Parse an event entry which can be a string or an object with overrides.
    
    Returns:
        tuple: (event_name, overrides_dict)
    """
    if isinstance(entry, str):
        # Backward compatibility: simple string format
        event_name = entry.strip().replace(' // present', '')
        return event_name, {}
    elif isinstance(entry, dict):
        # New format: object with event and optional overrides
        event_name = entry.get('event', '').strip()
        # All other keys are treated as overrides (except metadata keys)
        overrides = {k: v for k, v in entry.items() if k != 'event'}
        return event_name, overrides
    else:
        return None, {}

def group_events(events, variables=None):
    """Group events by control, handling DOWN/UP pairs and wheel events.
    
    Now supports event entries as either strings or objects with overrides.
    """
    if variables is None:
        variables = set()
    
    grouped = {}
    event_overrides = {}  # Store overrides per event name
    
    for entry in events:
        event_name, overrides = parse_event_entry(entry)
        if not event_name:
            continue
        
        # Store overrides for this event
        if overrides:
            event_overrides[event_name] = overrides
        
        event = event_name
            
        # Extract base name
        # Handle brightness wheel events (e.g., PED_DU1_BRT_KB_WHEEL_UP)
        if '_BRT_KB_WHEEL_' in event:
            # Extract base like: PED_DU1_BRT_KB (keep full prefix including _BRT_KB)
            base_match = re.match(r'(.+?_BRT_KB)_WHEEL_(UP|DOWN)', event)
            if base_match:
                base = base_match.group(1)
            else:
                base = event.split('_BRT_KB_WHEEL_')[0] + '_BRT_KB'
            is_wheel = True
        elif '_KB_WHEEL_' in event:
            # Match pattern like: OBS_AUDIO_PNL_ADF1_VOL_KB_WHEEL_UP
            # We want base: OBS_AUDIO_PNL_ADF1_VOL_KB (including _KB)
            base_match = re.match(r'(.+?_KB)_WHEEL_(UP|DOWN)', event)
            if base_match:
                # Keep the full base name including _KB (e.g., OBS_AUDIO_PNL_ADF1_VOL_KB)
                base = base_match.group(1)
            else:
                # Fallback: try without _KB requirement
                base_match = re.match(r'(.+?)_KB_WHEEL_(UP|DOWN)', event)
                if base_match:
                    base = base_match.group(1) + '_KB'
                else:
                    base = 'WHEEL'
            is_wheel = True
        elif '_BT_LEFT_BUTTON_DOWN' in event:
            # Keep _BT in base name to distinguish from _SW (e.g., LSIDE_TIMER_BT)
            base = event.replace('_BT_LEFT_BUTTON_DOWN', '_BT')
            is_wheel = False
        elif '_BT_LEFT_BUTTON_UP' in event:
            # Keep _BT in base name to distinguish from _SW
            base = event.replace('_BT_LEFT_BUTTON_UP', '_BT')
            is_wheel = False
        elif '_SW_LEFT_BUTTON_DOWN' in event:
            # Keep _SW in base name to distinguish from _BT (e.g., LSIDE_TIMER_SW)
            base = event.replace('_SW_LEFT_BUTTON_DOWN', '_SW')
            is_wheel = False
        elif '_SW_RIGHT_BUTTON_DOWN' in event:
            # Keep _SW in base name and add _RIGHT marker
            # For RIGHT buttons, we still group with the same control
            base = event.replace('_SW_RIGHT_BUTTON_DOWN', '_SW')
            is_wheel = False
        elif '_GRD_LEFT_BUTTON_DOWN' in event:
            # Keep _GRD in base name (e.g., CTR_SLAT_STOW_GRD)
            base = event.replace('_GRD_LEFT_BUTTON_DOWN', '_GRD')
            is_wheel = False
        else:
            # Fallback
            base = event
            is_wheel = False
        
        if base not in grouped:
            grouped[base] = {
                'DOWN': None,
                'UP': None,
                'LEFT': None,
                'RIGHT': None,
                'GRD': None,
                'events': [],
                'is_wheel': is_wheel,
                'l_variable': None,
                'control_type': None,
                'overrides': {}  # Store overrides for this group
            }
        
        grouped[base]['events'].append(event)
        
        # Store overrides for this event in the group
        if event in event_overrides:
            # Merge overrides (event-specific overrides take precedence)
            grouped[base]['overrides'].update(event_overrides[event])
        
        if '_WHEEL_DOWN' in event or '_BT_LEFT_BUTTON_DOWN' in event or '_SW_LEFT_BUTTON_DOWN' in event:
            grouped[base]['DOWN'] = event
        elif '_WHEEL_UP' in event or '_BT_LEFT_BUTTON_UP' in event:
            grouped[base]['UP'] = event
        elif '_SW_RIGHT_BUTTON_DOWN' in event:
            grouped[base]['RIGHT'] = event
        elif '_GRD_LEFT_BUTTON_DOWN' in event:
            grouped[base]['GRD'] = event
    
    # Check for L: variables for each group
    for base, group in grouped.items():
        if group['is_wheel'] and group['DOWN'] and group['UP']:
            # For wheel events, construct variable name from base name
            # Base is already extracted (e.g., OBS_AUDIO_PNL_ADF1_VOL_KB)
            var_name = f"MD11_{base}"
            if var_name in variables:
                group['l_variable'] = f"L:{var_name}"
                group['control_type'] = 'NumIncrement'
        elif not group['is_wheel'] and group['DOWN'] and group['UP']:
            # For button events, check if there's a corresponding L: variable (ToggleSwitch)
            l_var = find_l_variable(group['DOWN'], variables)
            if l_var:
                group['l_variable'] = l_var
                group['control_type'] = 'ToggleSwitch'
    
    return grouped

def format_override_lines(overrides):
    """Format override key-value pairs as YAML lines.
    
    Args:
        overrides: Dictionary of override key-value pairs
    
    Returns:
        List of formatted YAML lines
    """
    if not overrides:
        return []
    
    lines = []
    for key, value in sorted(overrides.items()):
        # Skip keys that are already handled by the generator
        if key in ['event', 'events']:  # Skip metadata keys
            continue
        
        # Format the value appropriately
        if isinstance(value, bool):
            lines.append(f"    {key}: {str(value).lower()}")
        elif isinstance(value, (int, float)):
            lines.append(f"    {key}: {value}")
        elif isinstance(value, str):
            lines.append(f"    {key}: {value}")
        else:
            lines.append(f"    {key}: {value}")
    
    return lines

def format_entry_as_yaml(entry):
    """Format a FS Copilot YAML entry dictionary back to YAML text format."""
    lines = []
    lines.append("  -")
    
    # FS Copilot format: sort keys with 'get' first, then 'set', then others
    key_order = ['get', 'set', 'skp']
    other_keys = [k for k in sorted(entry.keys()) if k not in key_order]
    ordered_keys = [k for k in key_order if k in entry] + other_keys
    
    for key in ordered_keys:
        value = entry[key]
        if isinstance(value, bool):
            lines.append(f"    {key}: {str(value).lower()}")
        elif isinstance(value, (int, float)):
            lines.append(f"    {key}: {value}")
        else:
            # String values - keep as-is (may contain JavaScript expressions)
            lines.append(f"    {key}: {value}")
    
    return lines

def is_standard_msfs_event(event_name):
    """Check if event is a standard MSFS event (uses >K:) or custom TFDi event (uses >B:)."""
    if not event_name:
        return False
    
    standard_prefixes = (
        'COM_', 'COM1_', 'COM2_', 'COM3_', 'NAV_', 'NAV1_', 'NAV2_', 'NAV3_', 'NAV4_',
        'ADF_', 'ADF1_', 'ADF2_', 'TRANSPONDER_', 'XPNDR_', 'TOGGLE_', 'SET_', 'AXIS_',
        'RUDDER_', 'ELEVATOR_', 'AILERON_', 'THROTTLE_', 'THROTTLE1_', 'THROTTLE2_', 'THROTTLE3_',
        'ELECTRICAL_', 'ENGINE_', 'FUEL_', 'LIGHT_', 'PITOT_', 'ANTI_ICE', 'BLEED_',
        'APU_', 'GENERAL_ENG_', 'RECIP_ENG_', 'TURB_ENG_', 'RADIO_', 'KOHLSMAN_',
        'HEADING_', 'SPEED_', 'ALTITUDE_', 'AUTOPILOT_', 'AP_', 'GPS_', 'MARKER_'
    )
    return any(event_name.startswith(prefix) for prefix in standard_prefixes)

def generate_fscopilot_set_expression(event_name, value_expr=None):
    """Generate FS Copilot set expression for an event.
    
    Uses >B: for custom TFDi events (bypasses CEVENT), >K: for standard MSFS events.
    For L: variable direct writes, uses >L: syntax.
    
    Args:
        event_name: Event name to trigger
        value_expr: Optional value expression (e.g., "value", "value + 1")
    
    Returns:
        String with set expression (quoted if contains JavaScript, unquoted if simple)
    """
    if not event_name:
        return None
    
    # Determine event type: custom TFDi events use >B: (bypasses CEVENT), standard MSFS events use >K:
    if is_standard_msfs_event(event_name):
        event_expr = f"(>K:{event_name})"
    else:
        # Custom TFDi event - use >B: (Behavior/H-event, bypasses CEVENT limitation)
        event_expr = f"(>B:{event_name})"
    
    if value_expr:
        # Value expression needed (e.g., "value (>K:EVENT)" or "value + 1 (>B:EVENT)")
        return f"`{value_expr} {event_expr}`"
    else:
        # Simple event trigger
        return event_expr

def generate_yaml(category_name, events, description, variables=None, merged_mode=False):
    """Generate FS Copilot format YAML content from events.
    
    Args:
        category_name: Name of the category
        events: List of event names
        description: Description for the category
        variables: Set of available L: variables
        merged_mode: If True, only generate shared section content (no headers)
    """
    if variables is None:
        variables = set()
    
    grouped = group_events(events, variables)
    xml_controls = get_xml_controls()
    
    lines = []
    if not merged_mode:
        lines.append(f"# TFDI MD-11 {description}")
        lines.append("# Events reference: https://docs.tfdidesign.com/md11/integration-guide/events")
        lines.append("# Variables reference: https://docs.tfdidesign.com/md11/integration-guide/variables")
        lines.append("")
        lines.append("shared:")
    
    # Sort groups for consistent output
    for base in sorted(grouped.keys()):
        group = grouped[base]
        comment = format_comment_name(group['events'][0] if group['events'] else base)
        
        # Handle wheel events with L: variables (increment/decrement)
        if group['is_wheel'] and group['l_variable'] and group['DOWN'] and group['UP']:
            # For wheel controls with L: vars, sync the variable value explicitly
            # FS Copilot syncs L: variable values, bypassing CEVENT entirely
            lines.append(f"  - # {comment}")
            lines.append(f"    get: {group['l_variable']}")
            # Explicit set to sync L: variable value directly (bypasses CEVENT)
            # When master rotates wheel, L: var value changes and syncs to all clients
            # Format: set: "value (>L:VAR_NAME)" - syncs the value both ways
            var_name_no_prefix = group['l_variable'].replace('L:', '')
            lines.append(f'    set: "`${{value}} (>L:{var_name_no_prefix})`"')
            lines.append("")
            
            # Note: Direct L: variable sync bypasses CEVENT limitation
            # When master rotates wheel, the aircraft's internal logic changes L: var value
            # FS Copilot syncs that value to all clients via explicit set
            continue
        
        # Handle wheel events without L: variables (direct event triggers)
        if group['is_wheel']:
            # For wheels without L: vars, trigger events directly when master uses wheel
            # These don't track state, so just trigger the event
            if group['UP']:
                lines.append(f"  - # {comment} (Wheel Up)")
                set_expr = generate_fscopilot_set_expression(group['UP'])
                lines.append(f'    set: {set_expr}')
                lines.append("")
            if group['DOWN']:
                lines.append(f"  - # {comment} (Wheel Down)")
                set_expr = generate_fscopilot_set_expression(group['DOWN'])
                lines.append(f'    set: {set_expr}')
                lines.append("")  # Blank line between groups
            continue
        
        # Handle button/switch events with L: variables (ToggleSwitch behavior)
        if group['l_variable'] and group['DOWN'] and group['UP']:
            # Check XML to see if it's actually a single-event switch (NUM_STATES=1)
            base_for_xml = base
            should_be_single_event = False
            if base_for_xml in xml_controls:
                control_info = xml_controls[base_for_xml]
                if control_info.get('num_states') == 1:
                    should_be_single_event = True
            
            lines.append(f"  - # {comment}")
            lines.append(f"    get: {group['l_variable']}")
            
            if should_be_single_event:
                # Single-event switch: trigger event when value changes
                # These switches toggle on each DOWN event regardless of current state
                set_expr = generate_fscopilot_set_expression(group['DOWN'])
                lines.append(f'    set: {set_expr}')
            else:
                # ToggleSwitch: Use JavaScript to trigger appropriate event based on value
                # When master changes L: variable value, trigger DOWN event (turn on) or UP event (turn off)
                # JavaScript: if value is 0/false (off), trigger DOWN to turn on; else trigger UP to turn off
                down_event = group['DOWN']
                up_event = group['UP']
                down_expr = generate_fscopilot_set_expression(down_event)
                up_expr = generate_fscopilot_set_expression(up_event)
                # Use JavaScript conditional: value ? UP_event : DOWN_event
                # Format as YAML string with single quotes for inner strings
                # Example: set: "value ? '(>B:EVENT_UP)' : '(>B:EVENT_DOWN)'"
                set_expr = f'value ? \'{up_expr}\' : \'{down_expr}\''
                lines.append(f'    set: "{set_expr}"')
            lines.append("")  # Blank line between groups
            continue
        
        # Handle button/switch events without L: variables (direct event triggers)
        # For simple events without state tracking, just trigger the event when master presses
        if group['DOWN']:
            lines.append(f"  - # {comment}")
            set_expr = generate_fscopilot_set_expression(group['DOWN'])
            lines.append(f'    set: {set_expr}')
            lines.append("")
        
        if group['UP'] and not group['l_variable']:
            # Separate entry for UP event if no L: var (no state tracking)
            if not group['DOWN']:
                lines.append(f"  - # {comment}")
            else:
                lines.append(f"  - # {comment} (Up)")
            set_expr = generate_fscopilot_set_expression(group['UP'])
            lines.append(f'    set: {set_expr}')
            lines.append("")
        
        if group['RIGHT']:
            lines.append(f"  - # {comment} (Right)")
            set_expr = generate_fscopilot_set_expression(group['RIGHT'])
            lines.append(f'    set: {set_expr}')
            lines.append("")
        
        if group['GRD']:
            lines.append(f"  - # {comment} (Guard)")
            set_expr = generate_fscopilot_set_expression(group['GRD'])
            lines.append(f'    set: {set_expr}')
            lines.append("")
        
        # Handle single events without DOWN/UP/RIGHT/GRD pattern
        if not group['DOWN'] and not group['UP'] and not group['RIGHT'] and not group['GRD']:
            for event in group['events']:
                if group['events'].index(event) > 0:
                    lines.append("")
                lines.append(f"  - # {comment}")
                set_expr = generate_fscopilot_set_expression(event)
                lines.append(f'    set: {set_expr}')
            if group['events']:
                lines.append("")  # Blank line after group
    
    return "\n".join(lines).rstrip() + "\n" if lines else ""

def generate_shared_content(category_name, events, description, variables=None):
    """Generate only the shared section content (for merged mode)."""
    content = generate_yaml(category_name, events, description, variables, merged_mode=True)
    # Remove the trailing newline and return
    return content.rstrip()

def validate_yaml_file(file_path):
    """Validate a YAML file and return error details if invalid."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            yaml.safe_load(content)
        return None  # Valid
    except yaml.YAMLError as e:
        error_msg = str(e)
        # Extract line number if available
        if hasattr(e, 'problem_mark'):
            mark = e.problem_mark
            line_num = mark.line + 1
            column = mark.column + 1
            # Get the problematic line
            lines = content.split('\n')
            if line_num <= len(lines):
                problem_line = lines[line_num - 1]
                return f"YAML Error at line {line_num}, column {column}:\n  {problem_line}\n  {' ' * (column - 1)}^\n{error_msg}"
            return f"YAML Error at line {line_num}, column {column}:\n{error_msg}"
        return f"YAML Error: {error_msg}"
    except Exception as e:
        return f"Error reading/validating YAML file: {e}"

def get_entry_key(entry):
    """Generate a unique key for a FS Copilot YAML entry to identify duplicates.
    
    Uses 'get' field as the unique identifier for FS Copilot format.
    """
    if isinstance(entry, dict):
        # FS Copilot format: use 'get' field as unique identifier
        if 'get' in entry:
            return ('get', entry['get'])
        # Fall back: use 'set' if no get
        if 'set' in entry:
            return ('set', entry['set'])
    return None

def parse_yaml_entries(yaml_content):
    """Parse YAML content and extract individual entries from the shared section.
    
    Returns a list of entry dictionaries and a mapping of keys to entries for deduplication.
    """
    try:
        data = yaml.safe_load(yaml_content)
        if not data or 'shared' not in data:
            return [], {}
        
        entries = []
        entry_map = {}
        
        for entry in data.get('shared', []):
            if not isinstance(entry, dict):
                continue
            
            key = get_entry_key(entry)
            if key:
                # Use the key to deduplicate - keep the first occurrence
                if key not in entry_map:
                    entry_map[key] = entry
                    entries.append(entry)
            else:
                # Entry without a clear key - keep it anyway
                entries.append(entry)
        
        return entries, entry_map
    except Exception as e:
        # If parsing fails, return empty (will regenerate from scratch)
        print(f"Warning: Could not parse existing YAML entries: {e}")
        return [], {}

def parse_aircraft_yaml(aircraft_file):
    """Parse the main aircraft YAML file to extract header, includes, shared, and master sections (FS Copilot format)."""
    # If file doesn't exist, return empty structure
    if not aircraft_file.exists():
        return {
            'header': '# TFDi Design MD-11 Configuration File for FS Copilot\n# Events reference: https://docs.tfdidesign.com/md11/integration-guide/events\n# Variables reference: https://docs.tfdidesign.com/md11/integration-guide/variables',
            'includes': 'include:',
            'shared': ['shared:'],
            'master': ''
        }
    
    with open(aircraft_file, 'r') as f:
        content = f.read()
    
    lines = content.split('\n')
    
    # Extract header (everything before 'include:')
    header_lines = []
    include_start = None
    for i, line in enumerate(lines):
        if line.strip() == 'include:':
            include_start = i
            break
        header_lines.append(line)
    
    if include_start is None:
        raise ValueError("Could not find 'include:' section in aircraft YAML file")
    
    # Extract includes (FS Copilot format: relative paths)
    include_lines = ['include:']
    shared_start = None
    for i in range(include_start + 1, len(lines)):
        line = lines[i]
        # Stop when we hit 'shared:' or a non-indented line
        if line.strip() == 'shared:' or (line and not line.startswith(' ') and line.strip() and not line.startswith('#')):
            shared_start = i
            break
        # Keep all includes (FS Copilot uses relative paths like 'modules/...')
        if line.strip().startswith('- '):
            include_lines.append(line)
    
    if shared_start is None:
        raise ValueError("Could not find 'shared:' section in aircraft YAML file")
    
    # Extract shared section (until 'master:')
    shared_lines = []
    master_start = None
    for i in range(shared_start, len(lines)):
        line = lines[i]
        if line.strip() == 'master:':
            master_start = i
            break
        shared_lines.append(line)
    
    # Extract master section (everything after 'master:')
    master_lines = []
    if master_start is not None:
        for i in range(master_start, len(lines)):
            master_lines.append(lines[i])
    
    return {
        'header': '\n'.join(header_lines).rstrip(),
        'includes': '\n'.join(include_lines),
        'shared': shared_lines,
        'master': '\n'.join(master_lines).rstrip() if master_lines else ''
    }

def merge_all_categories_to_aircraft_file(aircraft_file, data_dir, variables):
    """Merge all categories into the main aircraft YAML file (FS Copilot format)."""
    # Ensure output directory exists
    aircraft_file.parent.mkdir(parents=True, exist_ok=True)
    
    parsed = parse_aircraft_yaml(aircraft_file)
    
    # Extract manually-added entries by keeping lines that don't contain generated markers
    # FS Copilot format uses 'get:' and 'set:' instead of 'type:', 'var_name:', 'event_name:'
    manually_added_lines = []
    current_entry = []
    
    for line in parsed['shared'][1:]:  # Skip 'shared:' line
        stripped = line.lstrip()
        
        if stripped.startswith('-'):
            # New entry - check if previous entry was manually-added
            if current_entry:
                entry_text = '\n'.join(current_entry)
                # FS Copilot generated entries contain L:MD11_ variables or TFDi event patterns
                if not ('L:MD11_' in entry_text or 
                       'get: L:MD11_' in entry_text or
                       'set:' in entry_text and ('AOVHD_', 'OVHD_', 'PED_', 'OBS_', 'CTR_', 'LSIDE_', 'RSIDE_', 'CGS_', 'GSL_', 'GSR_', 'LECP_', 'RECP_', 'MIP_', 'THR_', 'YOKE_', 'CMCDU_', 'LMCDU_', 'RMCDU_' in entry_text)):
                    manually_added_lines.extend(current_entry)
                    manually_added_lines.append('')
                current_entry = []
            current_entry = [line]
        elif current_entry:
            current_entry.append(line)
        elif not stripped or stripped.startswith('#'):
            # Blank line or comment before any entry - keep if we have manual entries
            if manually_added_lines:
                manually_added_lines.append(line)
    
    # Check last entry
    if current_entry:
        entry_text = '\n'.join(current_entry)
        if not ('L:MD11_' in entry_text or 
               'get: L:MD11_' in entry_text or
               'set:' in entry_text and ('AOVHD_', 'OVHD_', 'PED_', 'OBS_', 'CTR_', 'LSIDE_', 'RSIDE_', 'CGS_', 'GSL_', 'GSR_', 'LECP_', 'RECP_', 'MIP_', 'THR_', 'YOKE_', 'CMCDU_', 'LMCDU_', 'RMCDU_' in entry_text)):
            manually_added_lines.extend(current_entry)
    
    # Generate fresh content from all categories
    category_files = sorted(data_dir.glob("*.json"))
    category_files = [f for f in category_files if f.name != "variables.json"]
    
    all_shared_content = []
    for category_file in category_files:
        category = category_file.stem
        try:
            with open(category_file) as f:
                data = json.load(f)
            
            events = data.get('events', [])
            description = data.get('description', category.replace('_', ' ').title())
            
            filtered_events = []
            for entry in events:
                event_name, overrides = parse_event_entry(entry)
                if event_name:
                    filtered_events.append(entry if isinstance(entry, dict) else event_name)
            
            if filtered_events:
                shared_content = generate_shared_content(category, filtered_events, description, variables)
                all_shared_content.append(shared_content)
                update_category_file(category_file, filtered_events)
        except Exception as e:
            print(f"  ERROR processing {category}: {e}")
            import traceback
            traceback.print_exc()
    
    # Reconstruct file (FS Copilot format)
    output_lines = [parsed['header'], "", parsed['includes'], "", "shared:"]
    
    if manually_added_lines:
        # Remove trailing blank lines
        while manually_added_lines and not manually_added_lines[-1].strip():
            manually_added_lines.pop()
        output_lines.extend(manually_added_lines)
        output_lines.append("")
    
    # Add generated content from all categories
    if all_shared_content:
        output_lines.append('\n'.join(all_shared_content))
    
    if parsed['master']:
        output_lines.append("")
        output_lines.append(parsed['master'])
    
    with open(aircraft_file, 'w') as f:
        content = '\n'.join(output_lines)
        if not content.endswith('\n'):
            content += '\n'
        f.write(content)
    
    validation_error = validate_yaml_file(aircraft_file)
    if validation_error:
        print(f"ERROR: Invalid YAML: {validation_error}")
        sys.exit(1)
    
    print(f"Merged {len(category_files)} categories into {aircraft_file}")

def update_aircraft_file_includes(aircraft_file, category_files):
    """Update the aircraft file to include all generated TFDI MD-11 modules (FS Copilot format)."""
    parsed = parse_aircraft_yaml(aircraft_file)
    
    # Build list of TFDI module includes (FS Copilot uses relative paths)
    tfdi_includes = []
    for category_file in sorted(category_files):
        category = category_file.stem
        # FS Copilot uses relative paths from Definitions/ folder
        tfdi_includes.append(f"  - modules/tfdi-md11/TFDi_MD11_{category}.yaml")
    
    # Reconstruct includes section: standard includes + TFDI includes
    include_lines = ['include:']
    # Add standard includes
    for line in parsed['includes'].split('\n')[1:]:  # Skip 'include:' line
        if line.strip():
            include_lines.append(line)
    # Add TFDI includes
    if tfdi_includes:
        include_lines.append("")
        include_lines.append("  # TFDI MD-11 Modules")
        include_lines.extend(tfdi_includes)
    
    # Reconstruct the file
    output_lines = []
    output_lines.append(parsed['header'])
    output_lines.append("")
    output_lines.append('\n'.join(include_lines))
    output_lines.append("")
    output_lines.append("shared:")
    
    # Add existing shared content
    # Fix indentation: ensure list items have 2 spaces
    existing_shared_lines = []
    for line in parsed['shared'][1:]:  # Skip 'shared:' line
        stripped = line.lstrip()
        # If line starts with '-' (list item), ensure it has 2 spaces indentation
        if stripped.startswith('-'):
            # Count current leading spaces
            leading_spaces = len(line) - len(stripped)
            if leading_spaces != 2:
                # Fix to 2 spaces
                existing_shared_lines.append('  ' + stripped)
            else:
                existing_shared_lines.append(line)
        else:
            existing_shared_lines.append(line)
    
    # Join lines but don't strip - we need to preserve leading spaces on first line
    existing_shared = '\n'.join(existing_shared_lines)
    # Only strip trailing whitespace, not leading
    existing_shared = existing_shared.rstrip()
    if existing_shared:
        output_lines.append(existing_shared)
    
    # Add master section if it exists
    if parsed['master']:
        output_lines.append("")
        output_lines.append(parsed['master'])
    
    # Write the file
    with open(aircraft_file, 'w') as f:
        f.write('\n'.join(output_lines))
        if not output_lines[-1].endswith('\n'):
            f.write('\n')
    
    # Validate the updated aircraft file
    validation_error = validate_yaml_file(aircraft_file)
    if validation_error:
        print(f"ERROR: Invalid YAML in aircraft file after updating includes")
        print(f"{validation_error}")
        sys.exit(1)
    
    print(f"Updated aircraft file includes: {len(tfdi_includes)} TFDI modules")

def update_existing_yaml(output_file, events, description, variables):
    """Update existing YAML file with new events, preserving structure."""
    if not output_file.exists():
        print(f"Error: File not found: {output_file}", file=sys.stderr)
        sys.exit(1)
    
    # For now, just regenerate (could be improved to do true merging)
    yaml_content = generate_yaml(output_file.stem.replace('TFDi_MD11_', ''), events, description, variables)
    
    with open(output_file, 'w') as f:
        f.write(yaml_content)
    
    print(f"Updated: {output_file}")

def clean_category_file(category_file):
    """Remove '// present' markers from category file."""
    with open(category_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Remove " // present" from event strings
    lines = content.split('\n')
    cleaned_lines = []
    for line in lines:
        cleaned_line = re.sub(r' // present', '', line)
        cleaned_lines.append(cleaned_line)
    
    cleaned_content = '\n'.join(cleaned_lines)
    
    with open(category_file, 'w', encoding='utf-8') as f:
        f.write(cleaned_content)
    
    # Count events
    with open(category_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return len(data.get('events', []))

def update_category_file(category_file, events):
    """Mark events as present in category file.
    
    Handles both string format and object format for events.
    """
    with open(category_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Extract event names from the events list (they may be strings or objects)
    event_names = set()
    for entry in events:
        event_name, _ = parse_event_entry(entry)
        if event_name:
            event_names.add(event_name)
    
    # Update events list
    updated_events = []
    for entry in data.get('events', []):
        event_name, overrides = parse_event_entry(entry)
        if not event_name:
            continue
        
        # Check if this event is in the generated events
        if event_name in event_names:
            # Mark as present, preserving format
            if isinstance(entry, str):
                # String format: add // present
                updated_events.append(f"{event_name} // present")
            elif isinstance(entry, dict):
                # Object format: keep the object as-is (overrides are preserved)
                updated_events.append(entry)
            else:
                updated_events.append(f"{event_name} // present")
        else:
            # Not present, keep original format
            if isinstance(entry, str):
                updated_events.append(event_name)
            elif isinstance(entry, dict):
                updated_events.append(entry)
            else:
                updated_events.append(event_name)
    
    data['events'] = updated_events
    # Count present events (check both string and object formats)
    present_count = sum(1 for e in updated_events 
                       if (isinstance(e, str) and '// present' in e) or 
                          (isinstance(e, dict) and e.get('event')))
    data['present_count'] = present_count
    data['total_count'] = len(updated_events)
    
    with open(category_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write('\n')  # Add trailing newline
    
    print(f"Updated category file: {category_file.name} ({present_count}/{len(updated_events)} events marked as present)")

def get_category_groups():
    """Define logical groupings of categories for modular output with system grouping.
    
    Categories are organized by physical location and system functionality
    to improve maintainability and organization of large configurations.
    
    Returns:
        Dictionary mapping group name to list of category names
    """
    return {
        'Glareshield': [
            'glareshield_left',
            'glareshield_right',
            'center_glareshield'
        ],
        'Overhead': [
            'overhead_panel',
            'aft_overhead_panel'
        ],
        'Pedestal': [
            'pedestal',
            'radio_panel',
            'audio_panel',
            'throttle'
        ],
        'Instruments': [
            'main_instruments_panel',
            'left_side_panel',
            'right_side_panel',
            'center_panel',
            'left_ecp',
            'right_ecp'
        ],
        'Flight_Controls': [
            'flight_controls',
            'left_yoke',
            'right_yoke'
        ],
        'FMC': [
            'fmc_cdu'
        ]
    }

def regenerate_all_modules(split_mode=False, grouped_split=False, custom_output_path=None):
    """Regenerate all TFDI MD-11 modules from scratch.
    
    Args:
        split_mode: If True, generate modular output files. If False (default), consolidate into main file.
        grouped_split: If True and split_mode is True, organize categories by cockpit system and panel location.
        custom_output_path: Optional custom output directory path for aircraft file
    """
    script_dir = Path(__file__).parent
    data_dir = script_dir / "tfdi-md11-data" / "json"
    # FS Copilot uses Definitions/modules/ folder structure
    modules_dir = script_dir / "Definitions" / "modules" / "tfdi-md11"
    aircraft_file = get_aircraft_file_path(custom_output_path)
    
    print("=" * 60)
    if split_mode:
        if grouped_split:
            print("REGENERATING ALL TFDI MD-11 MODULES (MODULAR - SYSTEM GROUPING)")
        else:
            print("REGENERATING ALL TFDI MD-11 MODULES (MODULAR - INDIVIDUAL CATEGORIES)")
    else:
        print("REGENERATING ALL TFDI MD-11 MODULES (CONSOLIDATED MODE)")
    print("=" * 60)
    
    # Step 1: Delete all TFDi_MD11_*.yaml files
    # In split mode, delete them to regenerate fresh
    # In merged mode (default), delete them since everything goes into the main file
    print("\nStep 1: Deleting existing TFDi_MD11_*.yaml files...")
    deleted_count = 0
    if modules_dir.exists():
        for module_file in modules_dir.glob("TFDi_MD11_*.yaml"):
            module_file.unlink()
            deleted_count += 1
            print(f"  Deleted: {module_file.name}")
    print(f"Deleted {deleted_count} module files")
    
    # Ensure the tfdi-md11 directory exists (needed for split mode)
    if split_mode:
        modules_dir.mkdir(parents=True, exist_ok=True)
    
    # Step 2: Clean all JSON category files (remove // present comments)
    print("\nStep 2: Cleaning JSON category files (removing // present comments)...")
    category_files = sorted(data_dir.glob("*.json"))
    # Exclude variables.json
    category_files = [f for f in category_files if f.name != "variables.json"]
    
    cleaned_count = 0
    for category_file in category_files:
        event_count = clean_category_file(category_file)
        cleaned_count += 1
        print(f"  Cleaned: {category_file.name} ({event_count} events)")
    print(f"Cleaned {cleaned_count} category files")
    
    # Step 3: Generate modules or merge into aircraft file
    print("\nStep 3: Generating modules...")
    variables = load_variables()
    
    if split_mode:
        if grouped_split:
            # Modular mode with system grouping: organize categories by cockpit system and panel location
            groups = get_category_groups()
            generated_count = 0
            
            # Create a reverse mapping: category -> group
            category_to_group = {}
            for group_name, categories in groups.items():
                for category in categories:
                    category_to_group[category] = group_name
            
            # Process each group
            for group_name, group_categories in groups.items():
                group_output_file = modules_dir / f"TFDi_MD11_{group_name}.yaml"
                
                # Collect all events from categories in this group
                all_group_events = []
                all_group_descriptions = []
                group_category_files_in_group = []
                
                for category_name in group_categories:
                    category_file = data_dir / f"{category_name}.json"
                    if not category_file.exists():
                        continue
                    if category_file not in category_files:
                        continue
                    
                    try:
                        with open(category_file) as f:
                            data = json.load(f)
                        
                        events = data.get('events', [])
                        description = data.get('description', category_name.replace('_', ' ').title())
                        
                        # Filter out "// present" markers
                        filtered_events = []
                        for entry in events:
                            event_name, overrides = parse_event_entry(entry)
                            if event_name:
                                if isinstance(entry, dict):
                                    filtered_events.append(entry)
                                else:
                                    filtered_events.append(event_name)
                        
                        if filtered_events:
                            all_group_events.extend(filtered_events)
                            all_group_descriptions.append(f"{description} ({len(filtered_events)} events)")
                            group_category_files_in_group.append(category_file)
                    except Exception as e:
                        print(f"  ERROR reading {category_file.name}: {e}")
                        continue
                
                if not all_group_events:
                    print(f"  Skipping {group_name} group (no events)")
                    continue
                
                # Generate combined YAML for the group
                combined_description = f"{group_name.replace('_', ' ')} ({', '.join(all_group_descriptions)})"
                yaml_content = generate_yaml(group_name, all_group_events, combined_description, variables)
                
                # Write output
                group_output_file.parent.mkdir(parents=True, exist_ok=True)
                with open(group_output_file, 'w') as f:
                    f.write(yaml_content)
                
                # Validate
                validation_error = validate_yaml_file(group_output_file)
                if validation_error:
                    print(f"  ERROR: Invalid YAML generated for {group_name}")
                    print(f"  {validation_error}")
                    raise ValueError(f"Invalid YAML in {group_output_file.name}")
                
                # Count entries
                get_with_lvar_count = yaml_content.count('get: L:MD11_')
                set_count = yaml_content.count('set:')
                
                print(f"  Generated: {group_name} ({len(all_group_events)} total events, {get_with_lvar_count} L: variable syncs, {set_count} event triggers)")
                
                # Update category files to mark events as present
                for category_file in group_category_files_in_group:
                    with open(category_file) as f:
                        cat_data = json.load(f)
                    cat_events = cat_data.get('events', [])
                    filtered_cat_events = []
                    for entry in cat_events:
                        event_name, overrides = parse_event_entry(entry)
                        if event_name:
                            filtered_cat_events.append(event_name)
                    update_category_file(category_file, filtered_cat_events)
                
                generated_count += 1
            
            # Handle categories not in any group (shouldn't happen, but be safe)
            ungrouped_files = []
            for category_file in category_files:
                category = category_file.stem
                if category not in category_to_group:
                    ungrouped_files.append(category_file)
            
            if ungrouped_files:
                print(f"\n  WARNING: {len(ungrouped_files)} categories not in any group, creating individual files:")
                for category_file in ungrouped_files:
                    category = category_file.stem
                    output_file = modules_dir / f"TFDi_MD11_{category}.yaml"
                    
                    try:
                        with open(category_file) as f:
                            data = json.load(f)
                        
                        events = data.get('events', [])
                        description = data.get('description', category.replace('_', ' ').title())
                        
                        filtered_events = []
                        for entry in events:
                            event_name, overrides = parse_event_entry(entry)
                            if event_name:
                                if isinstance(entry, dict):
                                    filtered_events.append(entry)
                                else:
                                    filtered_events.append(event_name)
                        events = filtered_events
                        
                        if not events:
                            continue
                        
                        yaml_content = generate_yaml(category, events, description, variables)
                        output_file.parent.mkdir(parents=True, exist_ok=True)
                        with open(output_file, 'w') as f:
                            f.write(yaml_content)
                        
                        validation_error = validate_yaml_file(output_file)
                        if validation_error:
                            print(f"    ERROR: Invalid YAML generated for {category}")
                            continue
                        
                        get_with_lvar_count = yaml_content.count('get: L:MD11_')
                        set_count = yaml_content.count('set:')
                        print(f"    Generated: {category} ({len(events)} events, {get_with_lvar_count} L: variable syncs, {set_count} event triggers)")
                        
                        update_category_file(category_file, events)
                        generated_count += 1
                    except Exception as e:
                        print(f"    ERROR generating {category}: {e}")
            
            print(f"\nGenerated {generated_count} grouped modules")
            
            # Update aircraft file to include all generated grouped modules
            grouped_output_files = []
            for group_name in groups.keys():
                group_file = modules_dir / f"TFDi_MD11_{group_name}.yaml"
                if group_file.exists():
                    # Create a dummy Path for the group (since we're grouping multiple categories)
                    grouped_output_files.append(group_file)
            
            # Also add any ungrouped individual files
            for category_file in ungrouped_files:
                category = category_file.stem
                output_file = modules_dir / f"TFDi_MD11_{category}.yaml"
                if output_file.exists():
                    grouped_output_files.append(output_file)
            
                # Update aircraft file includes with grouped files
            if grouped_output_files:
                # Update includes manually since we have grouped files
                parsed = parse_aircraft_yaml(aircraft_file)
                aircraft_file.parent.mkdir(parents=True, exist_ok=True)
                
                # Build includes list with grouped module paths
                include_lines = ['include:']
                # Add any existing standard includes (non-TFDi modules)
                for line in parsed['includes'].split('\n')[1:]:  # Skip 'include:' line
                    line = line.strip()
                    if line and not line.startswith('#') and 'TFDi_MD11' not in line:
                        include_lines.append(line)
                
                # Add grouped TFDi module includes
                if grouped_output_files:
                    include_lines.append("")
                    include_lines.append("  # TFDI MD-11 Modules (Grouped)")
                    for output_file in sorted(grouped_output_files):
                        # FS Copilot uses relative paths from Definitions/ folder
                        # Aircraft file is in Definitions/, grouped files are in Definitions/modules/tfdi-md11/
                        # So relative path is: modules/tfdi-md11/TFDi_MD11_GroupName.yaml
                        filename = output_file.name
                        include_path = f"modules/tfdi-md11/{filename}"
                        include_lines.append(f"  - {include_path}")
                
                # Reconstruct the file
                output_lines = []
                output_lines.append(parsed['header'])
                output_lines.append("")
                output_lines.append('\n'.join(include_lines))
                output_lines.append("")
                output_lines.append("shared:")
                
                # Add existing shared content
                existing_shared_lines = []
                for line in parsed['shared'][1:]:  # Skip 'shared:' line
                    stripped = line.lstrip()
                    if stripped.startswith('-'):
                        leading_spaces = len(line) - len(stripped)
                        if leading_spaces != 2:
                            existing_shared_lines.append('  ' + stripped)
                        else:
                            existing_shared_lines.append(line)
                    else:
                        existing_shared_lines.append(line)
                
                existing_shared = '\n'.join(existing_shared_lines).rstrip()
                if existing_shared:
                    output_lines.append(existing_shared)
                
                if parsed['master']:
                    output_lines.append("")
                    output_lines.append(parsed['master'])
                
                with open(aircraft_file, 'w') as f:
                    f.write('\n'.join(output_lines))
                    if not output_lines[-1].endswith('\n'):
                        f.write('\n')
                
                # Validate
                validation_error = validate_yaml_file(aircraft_file)
                if validation_error:
                    print(f"\nERROR: Invalid YAML in aircraft file after updating includes")
                    print(f"{validation_error}")
                    sys.exit(1)
        else:
            # Modular mode with individual categories: one file per category
            generated_count = 0
            for category_file in category_files:
                category = category_file.stem
                output_file = modules_dir / f"TFDi_MD11_{category}.yaml"
                
                try:
                    # Read category file
                    with open(category_file) as f:
                        data = json.load(f)
                    
                    events = data.get('events', [])
                    description = data.get('description', category.replace('_', ' ').title())
                    
                    # Filter out "// present" markers but preserve format
                    filtered_events = []
                    for entry in events:
                        event_name, overrides = parse_event_entry(entry)
                        if event_name:
                            if isinstance(entry, dict):
                                filtered_events.append(entry)
                            else:
                                filtered_events.append(event_name)
                    events = filtered_events
                    
                    if not events:
                        print(f"  Skipping {category} (no events)")
                        continue
                    
                    # Generate YAML
                    yaml_content = generate_yaml(category, events, description, variables)
                    
                    # Write output
                    output_file.parent.mkdir(parents=True, exist_ok=True)
                    with open(output_file, 'w') as f:
                        f.write(yaml_content)
                    
                    # Validate the generated YAML
                    validation_error = validate_yaml_file(output_file)
                    if validation_error:
                        print(f"  ERROR: Invalid YAML generated for {category}")
                        print(f"  {validation_error}")
                        raise ValueError(f"Invalid YAML in {output_file.name}")
                    
                    # Count FS Copilot format entries
                    get_with_lvar_count = yaml_content.count('get: L:MD11_')
                    set_count = yaml_content.count('set:')
                    
                    print(f"  Generated: {category} ({len(events)} events, {get_with_lvar_count} L: variable syncs, {set_count} event triggers)")
                    
                    # Update category file to mark events as present
                    update_category_file(category_file, events)
                    
                    generated_count += 1
                except Exception as e:
                    print(f"  ERROR generating {category}: {e}")
                    import traceback
                    traceback.print_exc()
        
        print(f"\nGenerated {generated_count} modules")
        
        # Update aircraft file to include all generated modules
        update_aircraft_file_includes(aircraft_file, category_files)
        
        # Validate the updated aircraft file
        validation_error = validate_yaml_file(aircraft_file)
        if validation_error:
            print(f"\nERROR: Invalid YAML in aircraft file after updating includes")
            print(f"{validation_error}")
            sys.exit(1)
    else:
        # Consolidated mode: write everything into main aircraft file
        merge_all_categories_to_aircraft_file(aircraft_file, data_dir, variables)
        print("\nMerged all categories into aircraft file")
        
        # Validate the merged aircraft file
        validation_error = validate_yaml_file(aircraft_file)
        if validation_error:
            print(f"\nERROR: Invalid YAML in aircraft file after merging")
            print(f"{validation_error}")
            sys.exit(1)
    
    # Step 4: Run validate on all categories
    print("\nStep 4: Running validate on all categories...")
    print("-" * 60)
    
    # Import validate module
    import importlib.util
    script_dir = Path(__file__).parent
    validate_path = script_dir / "validate.py"
    spec = importlib.util.spec_from_file_location("validate", validate_path)
    validate_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(validate_module)
    
    total_present = 0
    total_events = 0
    
    for category_file in category_files:
        try:
            present, total = validate_module.check_events_for_category(category_file)
            total_present += present
            total_events += total
        except Exception as e:
            print(f"ERROR checking {category_file.name}: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 60)
    print(f"FINAL SUMMARY: {total_present}/{total_events} events are present in YAML files")
    if total_events > 0:
        print(f"Coverage: {total_present/total_events*100:.1f}%")
    print("=" * 60)

def main():
    # Parse arguments
    custom_output_path = None
    processed_args = []
    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg in ['--output-path', '--output']:
            if i + 1 < len(sys.argv):
                custom_output_path = sys.argv[i + 1]
                i += 2  # Skip both flag and value
                continue
            else:
                print(f"Error: {arg} requires a path argument", file=sys.stderr)
                sys.exit(1)
        else:
            processed_args.append(arg)
            i += 1
    
    args = [arg for arg in processed_args if not arg.startswith('--')]
    flags = [arg for arg in processed_args if arg.startswith('--')]
    
    split_mode = '--split' in flags
    grouped_split = '--split-grouped' in flags
    
    # If no category specified, regenerate all
    if not args:
        regenerate_all_modules(split_mode=split_mode, grouped_split=grouped_split, custom_output_path=custom_output_path)
        return
    
    # Single category specified
    category = args[0]
    
    script_dir = Path(__file__).parent
    data_dir = script_dir / "tfdi-md11-data" / "json"
    category_file = data_dir / f"{category}.json"
    
    if not category_file.exists():
        print(f"Error: Category file not found: {category_file}", file=sys.stderr)
        sys.exit(1)
    
    # Load variables
    variables = load_variables()
    
    # Read category file
    with open(category_file) as f:
        data = json.load(f)
    
    events = data.get('events', [])
    description = data.get('description', category.replace('_', ' ').title())
    
    # Filter out "// present" markers but preserve format
    filtered_events = []
    for entry in events:
        event_name, overrides = parse_event_entry(entry)
        if event_name:
            if isinstance(entry, dict):
                filtered_events.append(entry)
            else:
                filtered_events.append(event_name)
    events = filtered_events
    
    if not events:
        print(f"No events found in {category}.json")
        return
    
    if split_mode:
        # Generate separate module file (FS Copilot format)
        script_dir = Path(__file__).parent
        # FS Copilot uses Definitions/modules/ folder structure
        modules_dir = script_dir / "Definitions" / "modules" / "tfdi-md11"
        modules_dir.mkdir(parents=True, exist_ok=True)
        output_file = modules_dir / f"TFDi_MD11_{category}.yaml"
        
        # Generate YAML
        yaml_content = generate_yaml(category, events, description, variables)
        
        # Write output
        with open(output_file, 'w') as f:
            f.write(yaml_content)
        
        # Validate the generated YAML
        validation_error = validate_yaml_file(output_file)
        if validation_error:
            print(f"ERROR: Invalid YAML generated for {category}")
            print(f"{validation_error}")
            sys.exit(1)
        
        print(f"Generated: {output_file}")
        print(f"Events: {len(events)}")
        
        # Count FS Copilot format entries
        get_with_lvar_count = yaml_content.count('get: L:MD11_')
        set_count = yaml_content.count('set:')
        if get_with_lvar_count > 0:
            print(f"L: variable syncs: {get_with_lvar_count}")
        if set_count > 0:
            print(f"Event triggers: {set_count}")
        
        # Update aircraft file to include this module
        aircraft_file = get_aircraft_file_path(custom_output_path)
        # Ensure output directory exists
        aircraft_file.parent.mkdir(parents=True, exist_ok=True)
        update_aircraft_file_includes(aircraft_file, [category_file])
        
        # Validate the updated aircraft file
        validation_error = validate_yaml_file(aircraft_file)
        if validation_error:
            print(f"\nERROR: Invalid YAML in aircraft file after updating includes")
            print(f"{validation_error}")
            sys.exit(1)
    else:
        # Merge this single category into the aircraft file (default behavior)
        aircraft_file = get_aircraft_file_path(custom_output_path)
        # Ensure output directory exists
        aircraft_file.parent.mkdir(parents=True, exist_ok=True)
        parsed = parse_aircraft_yaml(aircraft_file)
        
        # Generate shared content for this category
        shared_content = generate_shared_content(category, events, description, variables)
        
        # Parse new content to get entry keys for deduplication
        new_entries_map = {}
        try:
            new_yaml = yaml.safe_load(f"shared:\n{shared_content}")
            if new_yaml and 'shared' in new_yaml:
                for entry in new_yaml['shared']:
                    if isinstance(entry, dict):
                        key = get_entry_key(entry)
                        if key:
                            new_entries_map[key] = entry
        except:
            pass
        
        # Extract manually-added entries and filter out entries from this category (FS Copilot format)
        existing_shared_text = '\n'.join(parsed['shared'])
        manually_added = []
        
        try:
            existing_data = yaml.safe_load(existing_shared_text)
            if existing_data and isinstance(existing_data, dict):
                existing_entries = existing_data.get('shared')
                if existing_entries is None:
                    existing_entries = []
                elif not isinstance(existing_entries, list):
                    existing_entries = []
            else:
                existing_entries = []
        except Exception as e:
            # If parsing fails (e.g., old YourControls format), start fresh
            existing_entries = []
        
        for entry in existing_entries:
            if isinstance(entry, dict):
                get_var = str(entry.get('get', ''))
                set_expr = str(entry.get('set', ''))
                
                # Check if this entry is from the category we're regenerating
                key = get_entry_key(entry)
                is_from_category = key and key in new_entries_map
                
                # Keep if it's manually-added (no L:MD11_ vars or TFDi event patterns) 
                # AND not from the category we're regenerating
                if not is_from_category and not (
                    get_var.startswith('L:MD11_') or
                    'L:MD11_' in get_var or
                    (set_expr and any(pattern in set_expr for pattern in 
                     ('AOVHD_', 'OVHD_', 'PED_', 'OBS_', 'CTR_', 'LSIDE_', 'RSIDE_', 
                      'CGS_', 'GSL_', 'GSR_', 'LECP_', 'RECP_', 'MIP_', 'THR_', 
                      'YOKE_', 'CMCDU_', 'LMCDU_', 'RMCDU_', 'AOVHD_', 'OBS_')))
                ):
                    manually_added.append(entry)
        
        # Reconstruct file
        output_lines = [parsed['header'], "", parsed['includes'], "", "shared:"]
        
        # Add manually-added entries
        if manually_added:
            for entry in manually_added:
                lines = format_entry_as_yaml(entry)
                output_lines.extend(lines)
                output_lines.append("")
            output_lines.append("")
        
        # Add new category content
        output_lines.append(shared_content)
        
        if parsed['master']:
            output_lines.append("")
            output_lines.append(parsed['master'])
        
        with open(aircraft_file, 'w') as f:
            content = '\n'.join(output_lines)
            if not content.endswith('\n'):
                content += '\n'
            f.write(content)
        
        validation_error = validate_yaml_file(aircraft_file)
        if validation_error:
            print(f"ERROR: Invalid YAML: {validation_error}")
            sys.exit(1)
        
        print(f"Merged {category} into: {aircraft_file}")
        print(f"Events: {len(events)}")
        
        # Count FS Copilot format entries
        get_with_lvar_count = shared_content.count('get: L:MD11_')
        set_count = shared_content.count('set:')
        if get_with_lvar_count > 0:
            print(f"L: variable syncs: {get_with_lvar_count}")
        if set_count > 0:
            print(f"Event triggers: {set_count}")
    
    # Update category file to mark all events as present
    update_category_file(category_file, events)

if __name__ == '__main__':
    main()
