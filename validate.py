#!/usr/bin/env python3
"""
Check which events from category JSON files are already present in YAML definition files.
Updates the JSON files by appending " // present" to event names that are found.
"""

import json
import os
import re
from pathlib import Path

# Paths
script_dir = Path(__file__).parent
DATA_DIR = script_dir / "tfdi-md11-data" / "json"
AIRCRAFT_FILE = script_dir / "Definitions" / "TFDi_Design_MD-11.yaml"
MODULES_DIR = script_dir / "Definitions" / "modules" / "tfdi-md11"

def load_yaml_file(filepath):
    """Load YAML file content as text for searching."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return None

def find_event_in_yaml(event_name, yaml_content):
    """Check if event name appears in YAML content (FS Copilot format)."""
    if yaml_content is None:
        return False
    
    # Escape special regex characters in event name
    escaped_event = re.escape(event_name)
    
    # Look for FS Copilot format: set: (>B:EVENT_NAME) or set: (>K:EVENT_NAME)
    # Also check within JavaScript expressions: "value ? '(>B:EVENT_UP)' : '(>B:EVENT_DOWN)'"
    # And L: variable references: get: L:MD11_EVENT_NAME
    patterns = [
        rf'set:\s+\(>B:{escaped_event}\)',  # set: (>B:EVENT_NAME)
        rf'set:\s+\(>K:{escaped_event}\)',  # set: (>K:EVENT_NAME)
        rf'set:\s+"[^"]*\(>B:{escaped_event}\)[^"]*"',  # set: "..." (>B:EVENT_NAME) ..."
        rf'set:\s+"[^"]*\(>K:{escaped_event}\)[^"]*"',  # set: "..." (>K:EVENT_NAME) ..."
        rf"set:\s+'[^']*\(>B:{escaped_event}\)[^']*'",  # set: '...' (>B:EVENT_NAME) ...'
        rf"set:\s+'[^']*\(>K:{escaped_event}\)[^']*'",  # set: '...' (>K:EVENT_NAME) ...'
        rf"get:\s+L:MD11_{escaped_event}\b",  # get: L:MD11_EVENT_NAME
    ]
    
    for pattern in patterns:
        if re.search(pattern, yaml_content):
            return True
    
    return False

def get_module_filename(category_name):
    """Determine the module filename based on category name."""
    # Convert category name to module filename pattern
    # e.g., "audio_panel" -> "TFDi_MD11_audio_panel.yaml"
    # e.g., "aft_overhead_panel" -> "TFDi_MD11_aft_overhead_panel.yaml"
    module_name = f"TFDi_MD11_{category_name}.yaml"
    return MODULES_DIR / module_name

def check_events_for_category(category_file):
    """Check events for a specific category and update the JSON file."""
    print(f"\nChecking {category_file.name}...")
    
    # Load category JSON
    with open(category_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    category = data['category']
    events = data.get('events', [])
    
    # Remove any existing " // present" comments from event names
    events = [e.split(' // present')[0] for e in events]
    
    # Load YAML files to check
    aircraft_yaml = load_yaml_file(AIRCRAFT_FILE)
    module_yaml = load_yaml_file(get_module_filename(category))
    
    # Also check other module files that might contain events
    all_module_files = []
    if MODULES_DIR.exists():
        for module_file in MODULES_DIR.glob("TFDi_MD11_*.yaml"):
            if module_file.name != get_module_filename(category).name:
                all_module_files.append((module_file.name, load_yaml_file(module_file)))
    
    # Check each event
    present_count = 0
    updated_events = []
    
    for event in events:
        found = False
        found_in = []
        
        # Check main aircraft file
        if find_event_in_yaml(event, aircraft_yaml):
            found = True
            found_in.append("main")
        
        # Check corresponding module file
        if find_event_in_yaml(event, module_yaml):
            found = True
            found_in.append("module")
        
        # Check other module files
        for module_name, module_content in all_module_files:
            if find_event_in_yaml(event, module_content):
                found = True
                found_in.append(f"module:{module_name}")
        
        # Append " // present" if found
        if found:
            present_count += 1
            updated_events.append(f"{event} // present")
            print(f"  [FOUND] {event} (in: {', '.join(found_in)})")
        else:
            updated_events.append(event)
    
    # Update the events list
    data['events'] = updated_events
    data['event_count'] = len(updated_events)
    
    # Remove the events_with_status if it exists (from previous runs)
    if 'events_with_status' in data:
        del data['events_with_status']
    if 'present_events' in data:
        del data['present_events']
    if 'present_count' in data and data['present_count'] != present_count:
        # Only update if it changed, but we'll remove it for cleaner output
        pass
    
    # Save updated JSON
    with open(category_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"  Results: {present_count}/{len(events)} events present")
    return present_count, len(events)

def main():
    """Main function to check all category files."""
    import sys
    
    # Parse command line arguments
    target_file = None
    if len(sys.argv) > 1:
        target_arg = sys.argv[1].lower()
        # Handle various input formats: "fmc_cdu", "fmc_cdu.json", "fmc", etc.
        if "fmc" in target_arg or "cdu" in target_arg:
            target_file = "fmc_cdu.json"
        elif target_arg.endswith(".json"):
            target_file = target_arg
        else:
            # Try to find matching file
            possible_files = list(DATA_DIR.glob(f"{target_arg}*.json"))
            if possible_files:
                target_file = possible_files[0].name
            else:
                print(f"ERROR: No category file found matching '{target_arg}'")
                print(f"Available files: {', '.join([f.name for f in DATA_DIR.glob('*.json')])}")
                return
    
    print("Checking events in category files...")
    print(f"Aircraft file: {AIRCRAFT_FILE}")
    print(f"Modules directory: {MODULES_DIR}")
    
    if not AIRCRAFT_FILE.exists():
        print(f"ERROR: Aircraft file not found: {AIRCRAFT_FILE}")
        return
    
    if not MODULES_DIR.exists():
        print(f"WARNING: Modules directory not found: {MODULES_DIR}")
    
    # Get JSON files to process
    if target_file:
        category_file_path = DATA_DIR / target_file
        if not category_file_path.exists():
            print(f"ERROR: Category file not found: {target_file}")
            return
        category_files = [category_file_path]
        print(f"\nScanning only: {target_file}")
    else:
        # Get all JSON files in data directory
        category_files = sorted(DATA_DIR.glob("*.json"))
        # Exclude variables.json
        category_files = [f for f in category_files if f.name != "variables.json"]
        print(f"\nScanning all category files...")
    
    if not category_files:
        print("No category files found!")
        return
    
    total_present = 0
    total_events = 0
    
    for category_file in category_files:
        try:
            present, total = check_events_for_category(category_file)
            total_present += present
            total_events += total
        except Exception as e:
            print(f"ERROR processing {category_file.name}: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n{'='*60}")
    print(f"Summary: {total_present}/{total_events} events are present in YAML files")
    if total_events > 0:
        print(f"Coverage: {total_present/total_events*100:.1f}%")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
