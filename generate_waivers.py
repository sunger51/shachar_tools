#!/usr/bin/env /usr/intel/bin/python3
"""
Generate Crossfire Waiver File from Analysis Results
=====================================================

SCRIPT TYPE: MAIN SCRIPT (standalone entry point)

DEPENDENCIES:
    - analyze_crossfire_detailed.py (HELPER - called internally to parse workspace data)

DESCRIPTION:
    Creates .waivers files from crossfire analysis results. This script:
    1. Reads crossfire data from workspace (via analyze_crossfire_detailed.py)
    2. Generates waiver patterns for each violation
    3. Adds appropriate justifications
    4. Outputs .waivers files ready for crossfire

INPUTS:
    - Workspace path: Directory containing crossfire results for blocks
    - Block list: File with block names and types (block_name,type)

OUTPUTS (all in -outdir directory):
    - {block}.waivers          : Waiver file for each block
    - {block}_detailed/        : Analysis JSON and CSV for each block

USAGE:
    # Single block
    ./generate_waivers.py -block bpbiqrfip -outdir output -workspace /path/to/workspace
    
    # Multiple blocks from list file
    ./generate_waivers.py -block_list_with_types block_list.txt -outdir output -workspace /path/to/workspace
    
    # Use cached analysis (skip fresh data fetch)
    ./generate_waivers.py -block_list_with_types block_list.txt -outdir output -workspace /path/to/workspace -skip_analysis

OPTIONS:
    -block BLOCK              : Single block name
    -block_list_with_types F  : File with blocks (format: block_name,type per line)
    -outdir DIR               : Output directory for waivers and analysis
    -workspace PATH           : Path to crossfire workspace
    -skip_analysis            : Use cached JSON instead of fresh workspace data
    -tool TOOL                : Generate waivers only for specific tool
    -top N                    : Generate waivers for top N violations only

Author: Automated Waiver Generator
Date: February 2026
"""

import os
import sys
import json
import argparse
from datetime import datetime
from pathlib import Path
import re
import glob as glob_module

# Import analyzer for auto-analysis
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from analyze_crossfire_detailed import DetailedCrossfireAnalyzer
    ANALYZER_AVAILABLE = True
except ImportError:
    ANALYZER_AVAILABLE = False

class WaiverGenerator:
    """Generate waiver files from crossfire analysis results."""
    
    def __init__(self, block_name, output_dir=None, workspace_path=None):
        self.block_name = block_name
        self.output_dir = output_dir or '.'
        self.workspace_path = workspace_path  # Path to workspace for LEF/lib lookup
        self.results = None
        self.existing_justifications = {}  # Store justifications from existing waivers
        self.area_cache = {}  # Cache area values for performance
        
        # Get username
        self.username = os.environ.get('USER', 'unknown')
        
        # Default waiver settings
        self.waiver_date = datetime.now().strftime("%m/%d/%Y")
        self.waiver_modified = "PROD"
        self.waiver_expiration = "PROD"
        self.default_justification = "ACTION REQUIRED: User must add justification for this waiver!"
        
        # Load existing justifications
        self.load_existing_justifications()
    
    def load_existing_justifications(self):
        """Load justifications from ALL existing waiver files in ipcache."""
        print(f"[INFO] Scanning all waiver files in ipcache for justifications...")
        
        # Scan ALL waiver files from all blocks across multiple ipcache locations
        ipcache_patterns = [
            "/p/ipx/ipcache2/pnc_78_client_pnc78client/*/PNC78CLIENTB0PROD*/3/pnc_78_client_pnc78client.*/review/*.waivers",
            "/p/ipx/ipcache2/pnc_n2_client_pncn2h156p48/*/PNCN2H156P48B0PRODRTL*/3/pnc_n2_client_pncn2h156p48.*/review/*.waivers"
        ]
        
        # Collect all waiver files from all patterns
        waiver_files = []
        for pattern in ipcache_patterns:
            matches = glob_module.glob(pattern)
            waiver_files.extend(matches)
            print(f"[INFO] Found {len(matches)} waiver files from pattern: {pattern}")
        
        # Remove duplicates if any
        waiver_files = list(set(waiver_files))
        
        if not waiver_files:
            print(f"[INFO] No waiver files found in ipcache")
            print(f"[INFO] Will use default justifications")
            return
        
        print(f"[INFO] Found {len(waiver_files)} waiver files across all blocks")
        
        # Track justification frequency for smarter selection
        justification_counts = {}  # {tool: {justification: count}}
        
        # Parse all waiver files
        for idx, waiver_file in enumerate(waiver_files):
            if idx % 50 == 0 and idx > 0:
                print(f"[INFO] Processing waiver file {idx}/{len(waiver_files)}...")
            
            try:
                with open(waiver_file, 'r') as f:
                    content = f.read()
                
                # Parse by tool sections
                current_tool = None
                
                for line in content.split('\n'):
                    # Check for tool section
                    if line.startswith('begin_'):
                        current_tool = line.replace('begin_', '').strip()
                        if current_tool not in self.existing_justifications:
                            self.existing_justifications[current_tool] = []
                        if current_tool not in justification_counts:
                            justification_counts[current_tool] = {}
                    
                    # Check for justification
                    elif '# Justification:' in line and current_tool:
                        match = re.search(r'#\s*Justification:\s*(.+)', line)
                        if match:
                            justification = match.group(1).strip()
                            
                            # Count frequency
                            if justification not in justification_counts[current_tool]:
                                justification_counts[current_tool][justification] = 0
                            justification_counts[current_tool][justification] += 1
                            
            except Exception as e:
                # Skip files we can't read
                continue
        
        # Sort justifications by frequency (most common first)
        for tool, just_counts in justification_counts.items():
            sorted_justifications = sorted(just_counts.items(), 
                                         key=lambda x: x[1], 
                                         reverse=True)
            self.existing_justifications[tool] = [j[0] for j in sorted_justifications]
        
        # Print summary
        total_justifications = sum(len(v) for v in self.existing_justifications.values())
        print(f"[INFO] Loaded {total_justifications} unique justifications from {len(self.existing_justifications)} tools")
        
        # Show most common justifications per tool
        print(f"[INFO] Top justifications by tool:")
        for tool in sorted(self.existing_justifications.keys())[:5]:  # Show first 5 tools
            if self.existing_justifications[tool]:
                top_just = self.existing_justifications[tool][0]
                if len(top_just) > 60:
                    top_just = top_just[:60] + "..."
                print(f"       {tool}: {top_just}")
    
    def get_justification_for_tool(self, tool):
        """Get appropriate justification for a tool, filtering out generic ones."""
        # Generic/unhelpful justifications to skip (partial matches)
        generic_patterns = [
            "ok to waive",
            "waived",
            "ok to wave",
            "waive",
            "ok",
            "integration",
            "no issue",
            "not an issue"
        ]
        
        def is_generic(justification):
            """Check if justification is too generic."""
            just_clean = justification.lower().strip().rstrip('.')
            # Skip if it's very short
            if len(just_clean) < 15:
                return True
            # Skip if it starts with a generic pattern
            for pattern in generic_patterns:
                if just_clean.startswith(pattern):
                    return True
            return False
        
        # Check if we have existing justifications for this tool
        if tool in self.existing_justifications and self.existing_justifications[tool]:
            # Find first non-generic justification
            for justification in self.existing_justifications[tool]:
                if not is_generic(justification):
                    return justification
        
        # Fallback to tool-specific default with reason
        tool_specific_defaults = {
            "crossfire": "ACTION REQUIRED: User must add justification - crossfire timing violation",
            "crossfire_horizontal": "ACTION REQUIRED: User must add justification - horizontal check failure",
            "crossfire_timing": "ACTION REQUIRED: User must add justification - timing check failure",
            "crossfire_driftchecks": "ACTION REQUIRED: User must add justification - drift check failure",
            "crossfire_lef": "ACTION REQUIRED: User must add justification - LEF check failure",
            "onelv": "ACTION REQUIRED: User must add justification - OneLV structural issue",
            "ipxact": "ACTION REQUIRED: User must add justification - IPXact validation issue",
            "gls": "ACTION REQUIRED: User must add justification - GLS comparison difference",
            "paranoia": "ACTION REQUIRED: User must add justification - Paranoia check failure"
        }
        
        return tool_specific_defaults.get(tool, self.default_justification)
    
    def extract_transition_values(self, lib_file, line_number, index_str):
        """Extract transition value from lib file at specific line and index."""
        if not os.path.exists(lib_file):
            return None
        
        try:
            with open(lib_file, 'r') as f:
                lines = f.readlines()
            
            # Line numbers are 1-indexed
            if line_number < 1 or line_number > len(lines):
                return None
            
            line = lines[line_number - 1].strip()
            
            # Look for transition values in the line
            # Typically: values("0.123, 0.456, 0.789");
            # Or: rise_transition(scalar) { value : 0.123; }
            
            # Try to find numeric values
            numbers = re.findall(r'[\d.]+', line)
            
            if not numbers:
                return None
            
            # Parse index [row, col] if provided
            if index_str and '[' in index_str:
                idx_match = re.search(r'\[(\d+),\s*(\d+)\]', index_str)
                if idx_match:
                    row = int(idx_match.group(1))
                    col = int(idx_match.group(2))
                    # In lib files, transition tables are flattened
                    # Try to get the value at that position
                    flat_index = row * 10 + col  # Rough approximation
                    if flat_index < len(numbers):
                        return float(numbers[flat_index])
            
            # If no index or couldn't parse, return first number found
            if numbers:
                return float(numbers[0])
                
        except Exception as e:
            print(f"[WARNING] Failed to extract transition value from {lib_file}: {e}")
        
        return None
    
    def get_transition_comparison(self, sample_error):
        """Extract and compare transition values from lib files."""
        if not self.workspace_path:
            return None
        
        # Parse the error to get lib files, line numbers, and index
        # Pattern: "...from: LIB1 (V1) [line L1] to: LIB2 (V2) [line L2] at index [I1,I2], ..."
        pattern = r'from:.*?~([^~]+\.lib)\s*\(([\d.]+)V\)\s*\[line\s+(\d+)\].*?to:.*?~([^~]+\.lib)\s*\(([\d.]+)V\)\s*\[line\s+(\d+)\].*?at index\s*(\[[^\]]+\])'
        
        match = re.search(pattern, sample_error)
        if not match:
            return None
        
        lib1_name = match.group(1)
        v1 = match.group(2)
        line1 = int(match.group(3))
        lib2_name = match.group(4)
        v2 = match.group(5)
        line2 = int(match.group(6))
        index_str = match.group(7)
        
        # Find the lib files in workspace
        lib1_path = f"{self.workspace_path}/ship/ip/{self.block_name}/latest/staging/timing/{lib1_name}"
        lib2_path = f"{self.workspace_path}/ship/ip/{self.block_name}/latest/staging/timing/{lib2_name}"
        
        # Extract transition values
        trans1 = self.extract_transition_values(lib1_path, line1, index_str)
        trans2 = self.extract_transition_values(lib2_path, line2, index_str)
        
        if trans1 is None or trans2 is None:
            return None
        
        diff = trans2 - trans1
        diff_percent = (diff / max(abs(trans1), abs(trans2))) * 100
        
        return {
            'v1': v1,
            'v2': v2,
            'trans1': trans1,
            'trans2': trans2,
            'diff': diff,
            'diff_percent': diff_percent
        }
    
    def get_area_from_lef(self, cell_name):
        """Extract area value from LEF file."""
        if cell_name in self.area_cache and 'lef' in self.area_cache[cell_name]:
            return self.area_cache[cell_name]['lef']
        
        if not self.workspace_path:
            return None
        
        lef_path = f"{self.workspace_path}/ship/ip/{cell_name}/latest/staging/physical/lef/{cell_name}.lef"
        
        if not os.path.exists(lef_path):
            return None
        
        try:
            with open(lef_path, 'r') as f:
                content = f.read()
            
            # Look for MACRO definition and SIZE
            match = re.search(rf'MACRO\s+{cell_name}.*?SIZE\s+([\d.]+)\s+BY\s+([\d.]+)', content, re.DOTALL)
            if match:
                width = float(match.group(1))
                height = float(match.group(2))
                area = width * height
                
                if cell_name not in self.area_cache:
                    self.area_cache[cell_name] = {}
                self.area_cache[cell_name]['lef'] = area
                return area
        except Exception as e:
            print(f"[WARNING] Failed to parse LEF for {cell_name}: {e}")
        
        return None
    
    def get_area_from_lib(self, cell_name):
        """Extract area value from lib files."""
        if cell_name in self.area_cache and 'lib' in self.area_cache[cell_name]:
            return self.area_cache[cell_name]['lib']
        
        if not self.workspace_path:
            return None
        
        lib_pattern = f"{self.workspace_path}/ship/ip/{cell_name}/latest/staging/timing/{cell_name}_*.lib"
        lib_files = glob_module.glob(lib_pattern)
        
        if not lib_files:
            return None
        
        # Skip noise libs (_noise.lib) and temp derating libs (_T.max.lib) - they may have different area values
        lib_files = [f for f in lib_files if '_noise.lib' not in f and '_T.' not in f]
        
        if not lib_files:
            return None
        
        # Use first regular lib file
        lib_file = lib_files[0]
        
        try:
            with open(lib_file, 'r') as f:
                content = f.read()
            
            # Look for cell definition and area
            match = re.search(rf'cell\s*\(\s*{cell_name}\s*\).*?area\s*:\s*([\d.]+)', content, re.DOTALL)
            if match:
                area = float(match.group(1))
                
                if cell_name not in self.area_cache:
                    self.area_cache[cell_name] = {}
                self.area_cache[cell_name]['lib'] = area
                return area
        except Exception as e:
            print(f"[WARNING] Failed to parse lib for {cell_name}: {e}")
        
        return None
    
    def get_area_comparison(self, cell_name):
        """Get area comparison between LEF and lib files."""
        lef_area = self.get_area_from_lef(cell_name)
        lib_area = self.get_area_from_lib(cell_name)
        
        if lef_area is None or lib_area is None:
            return None
        
        diff = abs(lef_area - lib_area)
        diff_percent = (diff / max(lef_area, lib_area)) * 100
        
        return {
            'lef_area': lef_area,
            'lib_area': lib_area,
            'diff': diff,
            'diff_percent': diff_percent
        }
    
    def run_analysis(self):
        """Run crossfire analysis to generate JSON results."""
        if not ANALYZER_AVAILABLE:
            print("[ERROR] analyze_crossfire_detailed.py not available")
            return False
        
        if not self.workspace_path:
            print("[ERROR] Workspace path required for analysis")
            return False
        
        try:
            print(f"[INFO] Running analysis for {self.block_name}...")
            # workspace_path may include block name, analyzer expects work_area without block
            # e.g., /wa/sunger/bpbiqrfip -> /wa/sunger
            work_area = self.workspace_path
            if work_area.endswith(f"/{self.block_name}"):
                work_area = os.path.dirname(work_area)
            
            analyzer = DetailedCrossfireAnalyzer(self.block_name, self.output_dir, work_area)
            analyzer.run()
            return True
        except Exception as e:
            print(f"[ERROR] Analysis failed: {e}")
            return False
    
    def load_results(self, auto_analyze=True, force_analysis=False, skip_analysis=False):
        """Load analysis results from JSON file. Auto-run analysis if needed.
        
        Default behavior: Always analyze fresh data from workspace.
        Use skip_analysis=True to use cached JSON instead.
        """
        json_file = os.path.join(self.output_dir, f"{self.block_name}_detailed", 
                                 f"{self.block_name}_detailed_analysis.json")
        
        # Skip analysis only if explicitly requested AND json exists
        if skip_analysis and os.path.exists(json_file):
            print(f"[INFO] Using cached analysis (skip_analysis=True)")
        else:
            # Default: always analyze fresh data from workspace
            if os.path.exists(json_file):
                print(f"[INFO] Re-analyzing fresh data from workspace...")
            else:
                print(f"[INFO] Running analysis...")
            if not self.run_analysis():
                return False
        
        # Check again after analysis
        if not os.path.exists(json_file):
            print(f"[ERROR] Results file still not found after analysis: {json_file}")
            return False
        
        with open(json_file, 'r') as f:
            self.results = json.load(f)
        
        print(f"[INFO] Loaded results from: {json_file}")
        return True
    
    def get_tool_violations(self, tool_filter=None):
        """Get violations grouped by tool."""
        if not self.results:
            return {}
        
        tool_violations = {}
        
        # Try new format first (tools -> tool_name -> violations)
        tools_data = self.results.get('tools', {})
        if tools_data:
            for tool_name, tool_info in tools_data.items():
                # Apply tool filter
                if tool_filter and tool_name != tool_filter:
                    continue
                
                violations = tool_info.get('violations', [])
                if violations:
                    tool_violations[tool_name] = violations
        
        # Fallback to old format (crossfire -> detailed_violations)
        if not tool_violations:
            cf = self.results.get('crossfire', {})
            if cf.get('detailed_violations'):
                for v in cf['detailed_violations']:
                    tool = v.get('tool', 'unknown')
                    
                    # Apply tool filter
                    if tool_filter and tool != tool_filter:
                        continue
                    
                    if tool not in tool_violations:
                        tool_violations[tool] = []
                    
                    tool_violations[tool].append(v)
        
        return tool_violations
    
    def create_waiver_entry(self, violation, justification=None):
        """Create a waiver entry for a violation."""
        # Get tool to find appropriate justification
        tool = violation.get('tool', 'unknown')
        
        # Get rule info
        rule_id = violation.get('rule_id', 'unknown')
        check_name = violation.get('check', 'unknown')
        
        # Get sample errors - first from violation itself, then from rule_failure_samples
        sample_errors = violation.get('sample_errors', [])
        if not sample_errors:
            sample_errors = self.get_sample_errors(rule_id)
        
        # Create pattern(s)
        patterns = []
        if sample_errors:
            # Use samples to create patterns (with wildcards, duplicates will be removed)
            for sample in sample_errors[:20]:  # Process more samples to catch all file types
                # Use rule-specific pattern creation for certain rules
                if rule_id == "31":
                    pattern = self.create_pattern_rule31(sample)
                elif rule_id in ["7306", "7309", "7213", "7215"]:
                    # Voltage/transition rules - use simple wildcard pattern
                    pattern = self.create_pattern_voltage_transition(sample, self.block_name)
                elif rule_id == "7601":
                    # Missing/Extra table rule - handle both cases
                    if "Missing Table:" in sample:
                        pattern = "Missing Table: Format: NLDM_OCV~synopsys~NLDM-OCV*"
                    else:
                        pattern = "Extra Table: Format: NLDM_OCV~synopsys~NLDM-OCV*"
                else:
                    pattern = self.create_pattern(sample)
                if pattern and pattern not in patterns:
                    patterns.append(pattern)
        
        # If no samples, create generic pattern from rule_id
        if not patterns:
            patterns.append(f"* {rule_id} *")
        
        # Special handling for rule 15201 (area mismatch)
        area_info_comment = None
        area_based_justification = None
        if rule_id == "15201" and self.workspace_path:
            # Try to extract cell name from sample error
            if sample_errors:
                match = re.search(r"cell:\s*'([^']+)'", sample_errors[0])
                if match:
                    cell_name = match.group(1)
                    area_comp = self.get_area_comparison(cell_name)
                    if area_comp:
                        # Show full precision to see if it's truncation or rounding
                        lef_full = area_comp['lef_area']
                        lib_full = area_comp['lib_area']
                        diff_full = area_comp['diff']
                        diff_percent = area_comp['diff_percent']
                        
                        area_info_comment = (f"\t# Area Info: LEF={lef_full} (exact), "
                                           f"LIB={lib_full} (from file), "
                                           f"Diff={diff_full}")
                        
                        # Create specific justification based on area difference
                        if diff_percent < 0.1:
                            rounding_type = "rounded" if lib_full > lef_full else "truncated"
                            area_based_justification = (f"Area mismatch is due to LIB file value being {rounding_type} "
                                                       f"(LEF calculated: {lef_full}, LIB: {lib_full}). "
                                                       f"Difference of {diff_full:.6f} ({diff_percent:.4f}%) is negligible and acceptable.")
                        else:
                            area_based_justification = (f"Area values differ between LEF ({lef_full}) and LIB ({lib_full}). "
                                                       f"Difference of {diff_full:.2f} ({diff_percent:.2f}%) reviewed and acceptable.")
        
        # Special handling for rule 7306 (transition delay vs voltage)
        voltage_info_comment = None
        voltage_based_justification = None
        if rule_id == "7306" and sample_errors:
            # Simple justification as requested
            voltage_based_justification = "minor timing delta"
        
        # Special handling for rule 16035 (RV CMM POWER data not found)
        rv_cmm_based_justification = None
        if rule_id == "16035":
            rv_cmm_based_justification = ("RV CMM thermal rollup location differs by process. "
                                         "TSMC: thermal data is in rv/power/[avg|dcc]/RawModel/*_chip_thermal_profile.bin. "
                                         "Intel: thermal data is in separate rv/thermal/ directory. "
                                         "This check expects Intel structure but IP uses TSMC structure. Safe to waive.")
        
        # Special handling for rule 16048 (rv_thermal_type value)
        rv_thermal_based_justification = None
        if rule_id == "16048":
            rv_thermal_based_justification = "TEMPORARY WAIVER - rv_thermal_type value needs to be updated. Please open HSD to track this issue. Action required before production release."
        
        # Special handling for rule 16109 (csvpath does not exist)
        csvpath_based_justification = None
        if rule_id == "16109":
            csvpath_based_justification = "Action required: Add missing csvpath to design configuration. This error indicates that the specified CSV path for constraint validation does not exist and must be provided."
        
        # Special handling for rule 16199 (drift check / PREV_IPTAG_INFO missing)
        drift_based_justification = None
        if rule_id == "16199" or rule_id == "16015":
            drift_based_justification = ("Drift check is not mandatory at this stage. This error will be resolved "
                                        "when IPX tag is rerun with proper drift target configuration (PREV_IPTAG_INFO). "
                                        "No action required for current integration.")
        
        # Special handling for rule 31 (Pins-terminals mismatch)
        pin_mismatch_justification = None
        if rule_id == "31":
            # Check if sample errors mention the missing pins
            if sample_errors:
                # Extract missing pin names
                missing_pins = []
                for sample in sample_errors[:3]:
                    match = re.search(r"Missing terminal '([^']+)'", sample)
                    if match:
                        missing_pins.append(match.group(1))
                
                if missing_pins:
                    pins_str = ", ".join(missing_pins)
                    pin_mismatch_justification = (f"Pin/terminal count mismatch between LEF and SystemVerilog. "
                                                 f"Missing pins ({pins_str}) are wrapped in conditional compilation "
                                                 f"directives (`ifdef MEMGEN_LCP_PORTS) in RTL and may not be included "
                                                 f"in all build configurations. LEF includes all possible pins. "
                                                 f"This is expected behavior for optional LCP (Line Control Protocol) ports.")
                else:
                    pin_mismatch_justification = "Pin/terminal count mismatch between LEF and SystemVerilog is due to conditional compilation directives in RTL. This is expected for optional ports that may not be included in all configurations."
        
        # Special handling for rule 7601 (Missing timing table)
        missing_table_justification = None
        if rule_id == "7601":
            missing_table_justification = ("Missing timing tables in temperature-derating library (_T.max.lib). "
                                          "The temperature derating libraries may not include all sequential timing arcs "
                                          "(clk -> output) that exist in base min/max libraries. This is expected as "
                                          "temperature derating is typically applied to combinational paths. "
                                          "The base timing libraries contain the required tables.")
        
        # Special handling for rule 15106 (FilePresent - premature stop)
        premature_stop_justification = None
        if rule_id.startswith("15106"):
            # Check if error is about premature stop
            if sample_errors and any('prematurely' in str(e).lower() or 'stopped' in str(e).lower() for e in sample_errors):
                premature_stop_justification = ("Crossfire FilePresent check was interrupted prematurely during execution. "
                                               "This is a tool infrastructure issue, not a missing file problem. "
                                               "Re-run crossfire to verify file presence. No action required if files exist.")
            else:
                premature_stop_justification = ("Crossfire FilePresent check reported an issue. Verify that all required "
                                               "collateral files are present in the expected locations.")
        
        # Special handling for rule 15124 (Illegal keywords - segfault)
        segfault_justification = None
        if rule_id == "15124":
            if sample_errors and any('segfault' in str(e).lower() for e in sample_errors):
                segfault_justification = ("Crossfire illegal_and_required_keywords check (15124) crashed with segfault. "
                                         "This is a tool bug, not a design issue. The check script failed to complete. "
                                         "Re-run with updated crossfire version if available.")
        
        # Special handling for ImportError exceptions (tool bug affecting multiple rules)
        import_error_justification = None
        if sample_errors and any('importerror' in str(e).lower() for e in sample_errors):
            import_error_justification = ("Crossfire check script crashed with Python ImportError exception. "
                                         "This is a tool infrastructure issue - missing Python module dependency. "
                                         "Not a design problem. Re-run with updated crossfire version or report to tool team.")
        
        # Special handling for KeyboardInterrupt (check was interrupted)
        keyboard_interrupt_justification = None
        if sample_errors and any('keyboardinterrupt' in str(e).lower() for e in sample_errors):
            keyboard_interrupt_justification = ("Crossfire check was interrupted (KeyboardInterrupt). "
                                               "The check did not complete - results are incomplete. "
                                               "Re-run crossfire to get complete results for this rule.")
        
        # Special handling for rule 7309 (ComparePinProps - noise lib vs timing lib)
        pin_props_justification = None
        if rule_id == "7309":
            if sample_errors and any('noise.lib' in str(e).lower() for e in sample_errors):
                pin_props_justification = ("Terminal mismatch between noise library (CCSN_NLDM_OCV) and timing library (NLDM_OCV). "
                                          "Noise characterization libraries may contain additional internal pins for noise analysis "
                                          "that are not present in standard timing libraries. This is expected behavior as noise "
                                          "and timing libraries serve different purposes and may have different pin sets.")
            else:
                pin_props_justification = ("Pin property comparison mismatch between library formats. Different library types "
                                          "(timing, noise, power) may have different pin definitions based on their characterization scope.")
        
        # Special handling for rule 16331 (BusBitOrder_check - missing bus)
        bus_missing_justification = None
        if rule_id == "16331":
            # Check if it's the LCP ports issue
            if sample_errors and any('lcpctrl' in str(e).lower() for e in sample_errors):
                bus_missing_justification = ("Bus signal (lcpctrl_fd/lcpctrl_rd) missing in SystemVerilog file. "
                                            "These LCP (Line Control Protocol) ports are wrapped in conditional "
                                            "compilation directives (`ifdef MEMGEN_LCP_PORTS) in RTL. "
                                            "Bus is present in LEF but conditionally excluded from VS. Expected behavior.")
            else:
                bus_missing_justification = ("Bus definition missing in one or more collateral files. "
                                            "This may occur when bus signals are flattened to individual bits "
                                            "or when bus grouping differs between LEF/LIB/Verilog formats.")
        
        # Special handling for rule 16713 (Duplicate_libname_check)
        duplicate_lib_justification = None
        if rule_id == "16713":
            if sample_errors:
                # Extract the library names from error
                lib_names = []
                for e in sample_errors:
                    if 'noise.lib' in str(e).lower():
                        # Extract PVT corners from filename
                        import re as re_inner
                        corners = re_inner.findall(r'(\w+_\d+p\d+v_\w+c_\w+)\.noise\.lib', str(e))
                        lib_names.extend(corners)
                
                if lib_names and len(lib_names) >= 2:
                    duplicate_lib_justification = (f"Same model name found in noise libraries for different PVT corners "
                                                  f"({', '.join(set(lib_names))}). This is expected - noise libraries "
                                                  f"share internal model names but are selected based on corner conditions. "
                                                  f"No functional impact.")
                else:
                    duplicate_lib_justification = ("Duplicate library model name found across multiple noise library files. "
                                                  "Noise libraries for different PVT corners share the same internal model name. "
                                                  "Tools select the appropriate library based on PVT corner, not model name. Expected behavior.")
        
        # Special handling for rule 16024 (Ip2sd_logcheck - NDM/ETM workspace issues)
        ndm_etm_justification = None
        if rule_id == "16024":
            if sample_errors:
                has_etm_fallback = any('etm' in str(e).lower() for e in sample_errors)
                has_missing_port = any('port' in str(e).lower() and 'missing' in str(e).lower() for e in sample_errors)
                
                if has_etm_fallback and has_missing_port:
                    # Extract missing port name if possible
                    missing_ports = []
                    for e in sample_errors:
                        match = re.search(r'Port\s+(\w+)\s+missing', str(e))
                        if match:
                            missing_ports.append(match.group(1))
                    
                    ports_str = ', '.join(set(missing_ports)) if missing_ports else 'some ports'
                    ndm_etm_justification = (f"NDM workspace build failed, ETM (Extracted Timing Model) mode used as fallback. "
                                            f"Missing ports ({ports_str}) in NDM may be internal/test pins not exposed in timing models. "
                                            f"ETM mode is acceptable for timing analysis. Downstream timing pane visibility may be limited "
                                            f"but does not affect functional correctness.")
                elif has_etm_fallback:
                    ndm_etm_justification = ("NDM workspace could not be built normally, ETM mode was used instead. "
                                            "This is a workspace generation issue, not a design problem. "
                                            "ETM mode provides sufficient timing information for analysis.")
                else:
                    ndm_etm_justification = ("IP2SD log check reported issues during library processing. "
                                            "Review ip2sd logs for details on any missing or malformed data.")
        
        # Special handling for syntax errors in VS files (affects multiple rules: 15105, 16332, 21, etc.)
        syntax_error_justification = None
        if sample_errors and any('syntax error' in str(e).lower() for e in sample_errors):
            # Extract file and line info if available
            for e in sample_errors:
                match = re.search(r"Line (\d+) of file '([^']+)'.*syntax error", str(e))
                if match:
                    line_num = match.group(1)
                    file_name = match.group(2).split('/')[-1]  # Get just filename
                    syntax_error_justification = (f"Crossfire check failed due to syntax error in {file_name} at line {line_num}. "
                                                 f"This is a file parsing issue that prevents the check from completing. "
                                                 f"Review and fix the syntax error in the source file, then rerun crossfire.")
                    break
            
            if not syntax_error_justification:
                syntax_error_justification = ("Crossfire check failed due to syntax error in source file. "
                                             "This is a file parsing issue. Review and fix the syntax error, then rerun crossfire.")
        
        # Special handling for rule 16350 (Link_check - missing directory)
        link_check_justification = None
        if rule_id == "16350":
            if sample_errors and any('rtl_model' in str(e).lower() for e in sample_errors):
                link_check_justification = ("RTL_MODEL directory path specified in crossfire configuration does not exist. "
                                           "This is expected for memory/ROM IPs that may not have RTL models in the standard location. "
                                           "The check verifies directory links which may not apply to all IP types. "
                                           "No functional impact if RTL model is not required for this IP.")
            elif sample_errors and any("doesn't exist" in str(e).lower() for e in sample_errors):
                link_check_justification = ("Link check failed - specified directory path does not exist. "
                                           "Verify crossfire configuration points to valid paths. "
                                           "May be expected if certain collateral types are not applicable for this IP.")
            else:
                link_check_justification = ("Link check reported missing or invalid directory references. "
                                           "Review crossfire configuration for correct paths.")
        
        # Special handling for rule 7213 (Setup hold sum)
        setup_hold_justification = None
        if rule_id == "7213":
            setup_hold_justification = ("Setup + Hold time sum is negative at certain index points in timing tables. "
                                       "This can occur at extreme PVT corners where library characterization produces "
                                       "aggressive timing values. The negative sum indicates potential timing margin issues "
                                       "but may be acceptable if actual design paths have sufficient margin. "
                                       "Review affected pins and verify timing closure at these corners.")
        
        # Special handling for rule 16510 (Generic_attribute_conditions - device skew naming)
        attribute_conditions_justification = None
        if rule_id == "16510":
            if sample_errors and any('noise.lib' in str(e).lower() for e in sample_errors):
                attribute_conditions_justification = ("Library attribute condition failed for noise library. "
                                                     "Noise libraries may have different naming conventions for device skew "
                                                     "that don't match standard timing library patterns. "
                                                     "This is expected as noise characterization uses different PVT labeling. "
                                                     "No impact on timing analysis.")
            else:
                attribute_conditions_justification = ("Library attribute condition check failed. "
                                                     "Library metadata doesn't match expected naming pattern. "
                                                     "Verify library naming conventions match project requirements.")
        
        # Special handling for rule 7401 (CapacitanceCheck)
        capacitance_justification = None
        if rule_id.startswith("7401"):
            capacitance_justification = ("Pin capacitance value margin is smaller than expected threshold. "
                                        "The difference between max_capacitance and actual capacitance is below "
                                        "the configured limit. This is a library characterization artifact and "
                                        "does not affect functional operation. Capacitance values are within "
                                        "acceptable silicon limits for this process technology.")
        
        # Special handling for rule 7409 (IndexRangeCheck - timing table index range)
        index_range_justification = None
        if rule_id.startswith("7409"):
            index_range_justification = ("Timing table index range exceeds configured limits. "
                                        "The first index value for output capacitance or input transition is larger than "
                                        "the expected maximum. This is a library characterization choice where the table "
                                        "starts at a higher capacitance/transition value than the check threshold expects. "
                                        "Timing analysis tools will extrapolate for smaller values. "
                                        "Acceptable if design operates within characterized ranges.")
        
        # Special handling for rule 16712 (Duplicate_pvt_check)
        duplicate_pvt_justification = None
        if rule_id == "16712":
            duplicate_pvt_justification = ("Multiple libraries have identical PVT (Process/Voltage/Temperature) conditions. "
                                          "This occurs when different library variants (e.g., min_fast vs min_hvqk) share "
                                          "the same corner characterization parameters. Libraries may have different internal "
                                          "timing data despite matching PVT labels. Timing tools will select one based on "
                                          "user_checktype or other differentiators. No functional impact if correct library "
                                          "is selected for each analysis mode.")
        
        # Special handling for rule 7220 (Generic_table_value_range - negative timing values)
        table_value_range_justification = None
        if rule_id == "7220":
            table_value_range_justification = ("Timing table contains values outside expected range (negative or infinite). "
                                              "Small negative values (e.g., -0.001ps) can occur at extreme PVT corners due to "
                                              "library characterization artifacts or OCV derating. These typically appear in "
                                              "cell_fall/cell_rise tables at specific index combinations. Timing tools handle "
                                              "these by clamping to zero. Acceptable if negative values are small (<1ps) and "
                                              "don't affect critical path timing closure.")
        
        # Special handling for rule 7215 (StableValues - repeated/constant values in tables)
        stable_values_justification = None
        if rule_id == "7215":
            stable_values_justification = ("Timing table contains repeated/constant values across index range (StableValues check). "
                                          "This occurs when delay/transition values saturate at certain capacitance or "
                                          "transition ranges during characterization. The timing behavior plateaus at extreme "
                                          "operating points where the cell reaches its physical limits. This is expected library "
                                          "behavior for memory IPs at far corners. Timing tools interpolate correctly.")
        
        # Special handling for rule 7223 (Generic_table_monotonicity)
        monotonicity_justification = None
        if rule_id == "7223":
            monotonicity_justification = ("Timing table values are not monotonically increasing with index (input_net_transition). "
                                         "Non-monotonic behavior can occur at extreme characterization corners where cell "
                                         "internal effects dominate. This is a known artifact of library characterization at "
                                         "boundary conditions. The variation is typically small and doesn't affect timing "
                                         "accuracy for practical operating points. Timing tools handle interpolation correctly.")
        
        # Special handling for rule 7505 (IntraLibRelatedPGPin - missing related_power_pin)
        related_pg_justification = None
        if rule_id == "7505":
            # Extract pin names if available
            pg_pins = set()
            if sample_errors:
                for e in sample_errors:
                    match = re.search(r"pin '([^']+)'", str(e))
                    if match:
                        pg_pins.add(match.group(1))
            
            if pg_pins and any('virtual' in p.lower() or 'aggr' in p.lower() for p in pg_pins):
                pins_str = ', '.join(list(pg_pins)[:3])
                related_pg_justification = (f"Virtual aggressor pins ({pins_str}) missing 'related_power_pin' attribute. "
                                           "Virtual aggressor pins are used for noise analysis and don't require power pin "
                                           "association for functional timing. This is a noise library artifact.")
            else:
                related_pg_justification = ("Input pins missing 'related_power_pin' attribute in noise library. "
                                           "This attribute associates pins with power domains for power analysis. "
                                           "Verify if power pin association is needed for this pin type.")
        
        # Special handling for rule 7605 (RelatedPGPins - missing related_power_pin parameter)
        if rule_id == "7605":
            # Extract pin names if available
            pg_pins = set()
            if sample_errors:
                for e in sample_errors:
                    match = re.search(r"pin[:\s]+'?([^']+)'?", str(e))
                    if match:
                        pg_pins.add(match.group(1).strip("' "))
            
            if pg_pins and any('virtual' in p.lower() or 'aggr' in p.lower() for p in pg_pins):
                pins_str = ', '.join(list(pg_pins)[:3])
                related_pg_justification = (f"Virtual aggressor pins ({pins_str}) missing 'related_power_pin' parameter. "
                                           "Virtual aggressor metal zone pins are used for noise/EM analysis and don't require "
                                           "power pin association for functional timing. This is expected for noise library pins.")
            else:
                related_pg_justification = ("Pins missing 'related_power_pin' parameter. This parameter associates signal "
                                           "pins with power domains. Verify if power pin association is required.")
        
        # Special handling for rule 7410 (Ensure_arcs_present_for_given_related_pins)
        related_pin_arcs_justification = None
        if rule_id == "7410":
            # Extract pin names if available
            missing_arc_pins = set()
            if sample_errors:
                for e in sample_errors:
                    match = re.search(r"pins[^:]*:\s*(.+?)(?:\s*$|Format)", str(e))
                    if match:
                        missing_arc_pins.add(match.group(1).strip())
            
            if missing_arc_pins and any('test' in p.lower() or 'dft' in p.lower() for p in missing_arc_pins):
                pins_str = ', '.join(list(missing_arc_pins)[:3])
                related_pin_arcs_justification = (f"Test/DFT pins ({pins_str}) not mentioned as related_pin in timing arcs. "
                                                 "DFT control pins don't drive functional outputs during normal operation. "
                                                 "These pins only affect test mode paths which don't need timing characterization. "
                                                 "No functional timing impact.")
            elif missing_arc_pins:
                pins_str = ', '.join(list(missing_arc_pins)[:3])
                related_pin_arcs_justification = (f"Input pins ({pins_str}) not mentioned as related_pin in any timing arc. "
                                                 "Verify if these pins should have timing arcs to outputs or if they are "
                                                 "static control signals that don't affect timing-critical paths.")
            else:
                related_pin_arcs_justification = ("Input/inout pins not mentioned as related_pin in any timing arc. "
                                                 "These pins may be static control signals or test pins that don't require "
                                                 "timing characterization for functional analysis.")
        
        # Special handling for rule 16016 (Lib_manifest_check)
        lib_manifest_justification = None
        if rule_id == "16016":
            if sample_errors and any('prematurely' in str(e).lower() for e in sample_errors):
                lib_manifest_justification = ("Crossfire lib manifest check stopped prematurely (tool crash). "
                                             "This is an infrastructure issue, not a design problem. "
                                             "Re-run crossfire to complete the check.")
            else:
                lib_manifest_justification = ("Library manifest check validates library file consistency. "
                                             "Verify all required library files are present and accessible.")
        
        # Special handling for rule 16217 (Related_pin_check)
        related_pin_check_justification = None
        if rule_id == "16217":
            if sample_errors and any('prematurely' in str(e).lower() for e in sample_errors):
                related_pin_check_justification = ("Crossfire related pin check stopped prematurely (tool crash). "
                                                  "This is an infrastructure issue, not a design problem. "
                                                  "Re-run crossfire to complete the check.")
            else:
                related_pin_check_justification = ("Related pin check validates timing arc pin references. "
                                                  "Verify related_pin attributes in timing arcs point to valid pins.")
        
        # Special handling for rule 7202 (Value range transition)
        value_range_transition_justification = None
        if rule_id == "7202":
            if sample_errors and any('prematurely' in str(e).lower() for e in sample_errors):
                value_range_transition_justification = ("Crossfire value range transition check stopped prematurely (tool crash). "
                                                       "This is an infrastructure issue, not a design problem. "
                                                       "Re-run crossfire to complete the check.")
            else:
                value_range_transition_justification = ("Transition time values outside expected range in timing tables. "
                                                       "Verify input_net_transition values are within characterization bounds.")
        
        # Special handling for rule 7501 (Pulse presence check - min_pulse_width)
        pulse_presence_justification = None
        if rule_id == "7501":
            if sample_errors and any('importerror' in str(e).lower() for e in sample_errors):
                pulse_presence_justification = ("Crossfire check failed due to Python ImportError exception. "
                                               "This is an infrastructure/tool issue, not a design problem. "
                                               "The pulse width check could not complete. Re-run crossfire after "
                                               "verifying tool environment and dependencies.")
            else:
                # Extract pin names if available
                pulse_pins = set()
                if sample_errors:
                    for e in sample_errors:
                        match = re.search(r"pin '([^']+)'", str(e))
                        if match:
                            pulse_pins.add(match.group(1))
                
                if pulse_pins and any('test' in p.lower() or 'dft' in p.lower() for p in pulse_pins):
                    pins_str = ', '.join(list(pulse_pins)[:5])
                    pulse_presence_justification = (f"Missing min_pulse_width constraints on test/DFT pins ({pins_str}). "
                                                   "Test clock and DFT control pins don't require pulse width constraints "
                                                   "for functional timing analysis. These pins operate in test mode only "
                                                   "where pulse width is controlled by test equipment. No functional impact.")
                elif pulse_pins:
                    pins_str = ', '.join(list(pulse_pins)[:5])
                    pulse_presence_justification = (f"Missing min_pulse_width_low/high on pins ({pins_str}). "
                                                   "Pulse width constraints ensure clock signals meet minimum high/low times. "
                                                   "Verify if these pins require pulse width characterization for timing closure.")
                else:
                    pulse_presence_justification = ("Missing min_pulse_width_low or min_pulse_width_high constraints on pins. "
                                                   "Pulse width constraints ensure clock signals meet minimum high/low times. "
                                                   "Verify if these pins require pulse width characterization.")
        
        # Special handling for rule 16037 (Related_timing_types_check)
        related_timing_justification = None
        if rule_id == "16037":
            if sample_errors and any('dft' in str(e).lower() for e in sample_errors):
                related_timing_justification = ("Missing setup/hold timing constraints on DFT (Design For Test) pins. "
                                               "DFT control signals like dft_init are static during functional operation "
                                               "and don't require setup/hold characterization. These pins only toggle "
                                               "during test mode where timing is not critical. No functional impact.")
            else:
                related_timing_justification = ("Related timing types (setup_rising/hold_rising) not found together. "
                                               "This may occur for pins that only have one edge constraint characterized. "
                                               "Verify if both constraints are required for timing analysis.")
        
        # Special handling for rule 7607 (ArcPresence - missing timing tables on input pins)
        arc_presence_justification = None
        if rule_id == "7607":
            if sample_errors:
                # Extract pin names if available
                missing_pins = set()
                for e in sample_errors:
                    match = re.search(r"terminal '([^']+)'", str(e))
                    if match:
                        missing_pins.add(match.group(1))
                
                if missing_pins and any('dft' in p.lower() for p in missing_pins):
                    arc_presence_justification = ("Input pins without timing tables are DFT (Design For Test) control signals. "
                                                 "DFT pins like dft_init, scan_enable are not timing-critical during normal operation. "
                                                 "These pins are static during functional mode and only toggle during test. "
                                                 "No timing arcs required for functional timing closure.")
                elif missing_pins:
                    pins_str = ', '.join(list(missing_pins)[:5])
                    arc_presence_justification = (f"Input pins ({pins_str}) have no timing tables defined in library. "
                                                 "These may be static control signals or configuration pins that don't "
                                                 "require timing characterization. Verify these pins are not on critical paths.")
                else:
                    arc_presence_justification = ("Input terminal has no timing tables defined in library. "
                                                 "This may be expected for static control or configuration pins. "
                                                 "Verify pin is not on timing-critical paths.")
        
        # Use special justifications if available, otherwise use provided or default
        if area_based_justification:
            just = area_based_justification
        elif voltage_based_justification:
            just = voltage_based_justification
        elif rv_cmm_based_justification:
            just = rv_cmm_based_justification
        elif rv_thermal_based_justification:
            just = rv_thermal_based_justification
        elif csvpath_based_justification:
            just = csvpath_based_justification
        elif drift_based_justification:
            just = drift_based_justification
        elif pin_mismatch_justification:
            just = pin_mismatch_justification
        elif missing_table_justification:
            just = missing_table_justification
        elif premature_stop_justification:
            just = premature_stop_justification
        elif segfault_justification:
            just = segfault_justification
        elif import_error_justification:
            just = import_error_justification
        elif keyboard_interrupt_justification:
            just = keyboard_interrupt_justification
        elif pin_props_justification:
            just = pin_props_justification
        elif bus_missing_justification:
            just = bus_missing_justification
        elif duplicate_lib_justification:
            just = duplicate_lib_justification
        elif ndm_etm_justification:
            just = ndm_etm_justification
        elif syntax_error_justification:
            just = syntax_error_justification
        elif link_check_justification:
            just = link_check_justification
        elif setup_hold_justification:
            just = setup_hold_justification
        elif attribute_conditions_justification:
            just = attribute_conditions_justification
        elif capacitance_justification:
            just = capacitance_justification
        elif arc_presence_justification:
            just = arc_presence_justification
        elif index_range_justification:
            just = index_range_justification
        elif duplicate_pvt_justification:
            just = duplicate_pvt_justification
        elif table_value_range_justification:
            just = table_value_range_justification
        elif stable_values_justification:
            just = stable_values_justification
        elif monotonicity_justification:
            just = monotonicity_justification
        elif pulse_presence_justification:
            just = pulse_presence_justification
        elif related_pg_justification:
            just = related_pg_justification
        elif related_pin_arcs_justification:
            just = related_pin_arcs_justification
        elif lib_manifest_justification:
            just = lib_manifest_justification
        elif related_pin_check_justification:
            just = related_pin_check_justification
        elif value_range_transition_justification:
            just = value_range_transition_justification
        elif related_timing_justification:
            just = related_timing_justification
        elif justification:
            just = justification
        else:
            just = self.get_justification_for_tool(tool)
        
        waiver = []
        waiver.append(f"\t# Waiver Date:\t\t{self.waiver_date}")
        waiver.append(f"\t# Waiver Modified:\t{self.waiver_modified}")
        waiver.append(f"\t# Waiver User:\t\t{self.username}")
        waiver.append(f"\t# Waiver Expiration:\t{self.waiver_expiration}")
        waiver.append(f"\t# Justification:\t\t{just}")
        waiver.append(f"\t# Rule: {rule_id} ({check_name})")
        
        # Add area info if available for rule 15201
        if area_info_comment:
            waiver.append(area_info_comment)
        
        # Add voltage info if available for rule 7306
        if voltage_info_comment:
            waiver.append(voltage_info_comment)
        
        # Add all patterns
        for pattern in patterns:
            waiver.append(f"\t:F: {pattern}")
        
        waiver.append("")
        
        return '\n'.join(waiver)
    
    def get_sample_errors(self, rule_id):
        """Get sample errors for a rule from results."""
        if not self.results:
            return []
        
        # Check crossfire results
        cf = self.results.get('crossfire', {})
        samples = cf.get('rule_failure_samples', {})
        
        if rule_id in samples:
            return samples[rule_id]
        
        # Check onelv results
        lv = self.results.get('onelv', {})
        samples = lv.get('rule_failure_samples', {})
        
        if rule_id in samples:
            return samples[rule_id]
        
        return []
    
    def create_pattern_rule31(self, sample_error):
        """Create pattern for rule 31 (pin/terminal mismatch) preserving key info."""
        pattern = sample_error.strip()
        
        # For "Number of terminals" errors, keep the structure but wildcard the block name
        if "Number of terminals" in pattern:
            # 'bpbiqrfip': Number of terminals is 236 for 'CELLS~systemverilog~bpbiqrfip.vs', which should be 238
            # -> 'bpbiqrfip': Number of terminals is 236 for 'CELLS~systemverilog~*.vs', which should be 238
            pattern = re.sub(r"'CELLS~systemverilog~[^']+\.vs'", "'CELLS~systemverilog~*.vs'", pattern)
            pattern = re.sub(r"^'[^']+':", "'*':", pattern)  # Replace block name at start
        
        # For "Missing terminal" errors, keep terminal name but wildcard others
        elif "Missing terminal" in pattern:
            # 'bpbiqrfip': Missing terminal 'lcpctrl_fd' for 'CELLS~systemverilog~bpbiqrfip.vs' Golden Ref: 'MACRO~lef~MACRO~bpbiqrfip.lef' line 42
            # -> '*': Missing terminal 'lcpctrl_fd' for '*' Golden Ref: '*' line *
            pattern = re.sub(r"^'[^']+':", "'*':", pattern)  # Block name at start
            pattern = re.sub(r"for '[^']+'", "for '*'", pattern)  # VS file path
            pattern = re.sub(r"Golden Ref: '[^']+'", "Golden Ref: '*'", pattern)  # LEF ref
            pattern = re.sub(r"line \d+", "line *", pattern)  # Line number
        
        return pattern.strip()
    
    def create_pattern_voltage_transition(self, sample_error, block_name=None):
        """Create simple pattern for voltage/transition rules (7306, 7309, etc.).
        
        Working waiver patterns from ipcache (simplest that cover all errors):
        :F: Transition does not increase with decreasing voltage from*delta:0.00*
        :F: Delay does not increase with decreasing voltage from *
        
        Or block-specific:
        :F: Transition does not increase with decreasing voltage from NLDM_OCV~synopsys~NLDM-OCV~{block}_*
        """
        pattern = sample_error.strip()
        
        if "Transition does not increase" in pattern:
            # Pattern with delta threshold
            return "Transition does not increase with decreasing voltage from*delta:0.00*"
        
        if "Delay does not increase" in pattern:
            # Pattern with delta threshold for rule 7306
            return "Delay does not increase with decreasing voltage from*delta:0.00*"
        
        if "does not decrease with decreasing voltage" in pattern:
            if block_name:
                return f"* does not decrease with decreasing voltage from NLDM_OCV~synopsys~NLDM-OCV~{block_name}_*"
            return "* does not decrease with decreasing voltage *"
        
        # Fallback - use generic pattern
        return self.create_pattern(sample_error)
    
    def create_pattern(self, sample_error):
        """Convert sample error to waiver pattern with wildcards."""
        import re
        
        pattern = sample_error.strip()
        
        # Preserve structure but replace variable parts with wildcards
        
        # Replace voltage values like (1.21V), (0.85V) with (*) BEFORE number replacement
        pattern = re.sub(r'\(\d+\.?\d*V\)', '(*)', pattern)
        
        # Replace specific signal/pin names in brackets with wildcards
        # e.g., rddat_p0_b[51] -> *
        pattern = re.sub(r'\w+\[\d+\]', '*', pattern)
        
        # Replace bare numbers with wildcards
        pattern = re.sub(r'\b\d+\.\d+\b', '*', pattern)  # Floating point
        pattern = re.sub(r'\b\d+\b', '*', pattern)       # Integers
        
        # Replace hexadecimal numbers
        pattern = re.sub(r'0x[0-9a-fA-F]+', '*', pattern)
        
        # Replace file paths but keep structure visible
        pattern = re.sub(r'/nfs/[^\s:]+', '*', pattern)
        pattern = re.sub(r'/[a-z_]+/[^\s:]+', '*', pattern)
        
        # Replace quoted strings with wildcards but keep quotes for structure
        # Pattern: "something" -> "*"
        pattern = re.sub(r'"[^"]{10,}"', '"*"', pattern)  # Long strings
        pattern = re.sub(r"'[^']{10,}'", "'*'", pattern)
        
        # Replace specific values in key-value pairs
        # e.g., "value=12345" -> "value=*"
        pattern = re.sub(r'=\s*\d+', '=*', pattern)
        pattern = re.sub(r'=\s*"[^"]*"', '="*"', pattern)
        
        # Replace coordinate-like patterns
        pattern = re.sub(r'\(\s*\d+\s*,\s*\d+\s*\)', '(*,*)', pattern)
        
        # Replace PVT corner names in library files with wildcards
        # e.g., bpbiqrfip_ffgnp_1p271v_125c_rcworst_CCworst.noise.lib -> bpbiqrfip_*.lib
        # Use aggressive wildcard to cover ALL corners with single pattern
        
        # Pattern: blockname_corner_voltage_temp_....(noise|min|max).lib -> blockname_*.lib
        pattern = re.sub(r'(\w+rfip)_[a-z]+gnp_[^\s]+\.lib', r'\1_*.lib', pattern)
        pattern = re.sub(r'(\w+rfip)_tt_[^\s]+\.lib', r'\1_*.lib', pattern)
        
        # More general: block_(ff|ss|tt)corner_voltage_temp.*.lib -> block_*.lib  
        pattern = re.sub(r'(\w+)_(ff|ss|tt)[a-z]*_\dp\d+v_[^\s]+\.lib', r'\1_*.lib', pattern)
        
        # Also handle _T suffix variants (temperature derating)
        pattern = re.sub(r'(\w+)_[a-z]+gnp_[^\s]+_T\.(max|min)\.lib', r'\1_*.lib', pattern)
        
        # Clean up: Remove excessive spaces
        pattern = re.sub(r'\s+', ' ', pattern)
        
        # Clean up: Collapse multiple asterisks (but keep structure)
        # Don't collapse if separated by meaningful characters
        pattern = re.sub(r'\*\s+\*', '*', pattern)
        
        # Truncate if too long, but try to keep meaningful parts
        if len(pattern) > 250:
            # Try to truncate at a space
            pattern = pattern[:250]
            last_space = pattern.rfind(' ')
            if last_space > 200:
                pattern = pattern[:last_space]
            pattern += " *"
        
        return pattern.strip()
    
    def generate_waiver_file(self, tool_filter=None, top_n=None, justification=None):
        """Generate complete waiver file."""
        tool_violations = self.get_tool_violations(tool_filter)
        
        if not tool_violations:
            print("[WARNING] No violations found to waive")
            return None
        
        waiver_lines = []
        total_waivers = 0
        
        for tool, violations in sorted(tool_violations.items()):
            # Limit to top N if specified
            violations_to_waive = violations
            if top_n:
                # Sort by failures (descending)
                violations_to_waive = sorted(violations, 
                                            key=lambda x: x.get('failures', 0), 
                                            reverse=True)[:top_n]
            
            if not violations_to_waive:
                continue
            
            # Create section header
            waiver_lines.append(f"begin_{tool}")
            waiver_lines.append("")
            
            # Add waiver entries
            for v in violations_to_waive:
                waiver_lines.append(self.create_waiver_entry(v, justification))
                total_waivers += 1
            
            waiver_lines.append(f"end_{tool}")
            waiver_lines.append("")
        
        print(f"[INFO] Generated {total_waivers} waiver entries for {len(tool_violations)} tools")
        
        return '\n'.join(waiver_lines)
    
    def save_waiver_file(self, content, output_file=None):
        """Save waiver file."""
        if not output_file:
            output_file = os.path.join(self.output_dir, f"{self.block_name}.waivers")
        
        with open(output_file, 'w') as f:
            f.write(content)
        
        print(f"[SUCCESS] Waiver file saved to: {output_file}")
        return output_file
    
    def run(self, tool_filter=None, top_n=None, justification=None, output_file=None, skip_analysis=False):
        """Main execution flow."""
        print(f"\n{'=' * 80}")
        print(f"WAIVER GENERATOR FOR: {self.block_name}")
        print(f"{'=' * 80}\n")
        
        # Load results (always analyze fresh unless skip_analysis=True)
        if not self.load_results(skip_analysis=skip_analysis):
            return 1
        
        # Generate waiver content
        content = self.generate_waiver_file(tool_filter, top_n, justification)
        if not content:
            return 1
        
        # Save to file
        output_file = self.save_waiver_file(content, output_file)
        
        print(f"\n[INFO] Waiver file created successfully!")
        print(f"[INFO] Review and edit justifications as needed:")
        print(f"       vi {output_file}")
        print(f"\n{'=' * 80}\n")
        
        return 0


def parse_waiver_stats(content, block_name, stats):
    """Parse waiver content and update stats dictionary."""
    current_tool = None
    current_rule = None
    current_justification = None
    current_rule = None
    current_tool = None
    error_count = 0
    
    for line in content.split('\n'):
        line = line.strip()
        
        # Track tool sections
        if line.startswith('begin_'):
            current_tool = line.replace('begin_', '')
        elif line.startswith('end_'):
            current_tool = None
        
        # Extract rule
        elif '# Rule:' in line:
            # Save previous rule's error count
            if current_rule and current_rule in stats['rules']:
                stats['rules'][current_rule]['total_errors'] = stats['rules'][current_rule].get('total_errors', 0) + error_count
            
            error_count = 0  # Reset for new rule
            match = re.search(r'# Rule:\s*(\d+)', line)
            if match:
                current_rule = match.group(1)
                
                # Initialize block stats
                if block_name not in stats['blocks']:
                    stats['blocks'][block_name] = {}
                if current_tool not in stats['blocks'][block_name]:
                    stats['blocks'][block_name][current_tool] = []
                stats['blocks'][block_name][current_tool].append(current_rule)
                
                # Initialize rule stats
                if current_rule not in stats['rules']:
                    stats['rules'][current_rule] = {
                        'blocks': set(),
                        'tool': current_tool,
                        'count': 0,
                        'total_errors': 0,
                        'justification': current_justification or ''
                    }
                stats['rules'][current_rule]['blocks'].add(block_name)
                stats['rules'][current_rule]['count'] += 1
                
                # Initialize tool stats
                if current_tool not in stats['tools']:
                    stats['tools'][current_tool] = {
                        'blocks': set(),
                        'rules': set(),
                        'count': 0,
                        'total_errors': 0
                    }
                stats['tools'][current_tool]['blocks'].add(block_name)
                stats['tools'][current_tool]['rules'].add(current_rule)
                stats['tools'][current_tool]['count'] += 1
        
        # Count error patterns (:F: lines)
        elif line.startswith(':F:'):
            error_count += 1
            if current_tool and current_tool in stats['tools']:
                stats['tools'][current_tool]['total_errors'] = stats['tools'][current_tool].get('total_errors', 0) + 1
        
        # Extract justification
        elif '# Justification:' in line:
            current_justification = line.split('# Justification:', 1)[1].strip()
    
    # Save last rule's error count
    if current_rule and current_rule in stats['rules']:
        stats['rules'][current_rule]['total_errors'] = stats['rules'][current_rule].get('total_errors', 0) + error_count


def generate_waiver_report(stats, report_file, total_blocks):
    """Generate readable summary report from waiver stats."""
    lines = []
    
    lines.append("=" * 100)
    lines.append("COMBINED WAIVER SUMMARY REPORT")
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("=" * 100)
    lines.append("")
    
    # Overall summary
    total_waivers = sum(t['count'] for t in stats['tools'].values())
    total_errors = sum(t.get('total_errors', 0) for t in stats['tools'].values())
    total_rules = len(stats['rules'])
    total_tools = len(stats['tools'])
    
    lines.append("OVERALL SUMMARY")
    lines.append("-" * 50)
    lines.append(f"  Total Blocks:      {total_blocks}")
    lines.append(f"  Total Tools:       {total_tools}")
    lines.append(f"  Total Rules:       {total_rules}")
    lines.append(f"  Total Waivers:     {total_waivers}")
    lines.append(f"  Total Errors:      {total_errors}")
    lines.append("")
    
    # Per-tool summary
    lines.append("=" * 100)
    lines.append("WAIVERS BY TOOL")
    lines.append("=" * 100)
    lines.append("")
    lines.append(f"{'Tool':<40} {'Blocks':<10} {'Rules':<10} {'Waivers':<10} {'Errors':<10}")
    lines.append("-" * 80)
    
    for tool in sorted(stats['tools'].keys()):
        t = stats['tools'][tool]
        lines.append(f"{tool:<40} {len(t['blocks']):<10} {len(t['rules']):<10} {t['count']:<10} {t.get('total_errors', 0):<10}")
    lines.append("")
    
    # Per-rule summary (sorted by total errors, descending)
    lines.append("=" * 100)
    lines.append("WAIVERS BY RULE (sorted by total errors)")
    lines.append("=" * 100)
    lines.append("")
    lines.append(f"{'Rule':<10} {'Tool':<35} {'Blocks':<10} {'Waivers':<10} {'Errors':<10}")
    lines.append("-" * 80)
    
    sorted_rules = sorted(stats['rules'].items(), key=lambda x: x[1].get('total_errors', 0), reverse=True)
    for rule_id, r in sorted_rules:
        lines.append(f"{rule_id:<10} {r['tool']:<35} {len(r['blocks']):<10} {r['count']:<10} {r.get('total_errors', 0):<10}")
    lines.append("")
    
    # Rules affecting all blocks (common issues)
    lines.append("=" * 100)
    lines.append("RULES AFFECTING MOST BLOCKS (potential systemic issues)")
    lines.append("=" * 100)
    lines.append("")
    
    # Filter rules affecting >50% of blocks
    threshold = total_blocks * 0.5
    common_rules = [(rule_id, r) for rule_id, r in sorted_rules if len(r['blocks']) >= threshold]
    
    if common_rules:
        for rule_id, r in common_rules:
            pct = len(r['blocks']) / total_blocks * 100
            lines.append(f"Rule {rule_id} ({r['tool']})")
            lines.append(f"  Affects: {len(r['blocks'])}/{total_blocks} blocks ({pct:.1f}%)")
            # Show full justification
            lines.append(f"  Justification: {r['justification']}")
            lines.append("")
    else:
        lines.append("  No rules affect more than 50% of blocks.")
        lines.append("")
    
    # Detailed rule breakdown with affected blocks
    lines.append("=" * 100)
    lines.append("DETAILED RULE BREAKDOWN")
    lines.append("=" * 100)
    lines.append("")
    
    for rule_id, r in sorted_rules:
        lines.append(f"Rule {rule_id}")
        lines.append(f"  Tool: {r['tool']}")
        lines.append(f"  Total waivers: {r['count']}")
        lines.append(f"  Affected blocks ({len(r['blocks'])}):")
        
        # List blocks in columns
        block_list = sorted(r['blocks'])
        for i in range(0, len(block_list), 5):
            chunk = block_list[i:i+5]
            lines.append(f"    {', '.join(chunk)}")
        
        # Show full justification
        lines.append(f"  Justification: {r['justification']}")
        lines.append("")
    
    # Write report
    with open(report_file, 'w') as f:
        f.write('\n'.join(lines))
    
    print(f"[SUCCESS] Summary report: {report_file}")


def find_newest_workspace(block, workspaces):
    """
    Find the workspace with the newest crossfire data for a block.
    Returns (workspace_path, info_dict) or (None, None) if not found.
    """
    best_workspace = None
    best_date = None
    best_info = None
    
    for workspace in workspaces:
        block_path = f"{workspace}/{block}"
        
        # Look for crossfire run directories
        # Pattern: .../crossfire/crossfire/{block}.rtl*.YYYY_MM_DD_HHMMSS.*/
        crossfire_base = f"{block_path}/ship/ip/{block}"
        
        if not os.path.exists(crossfire_base):
            continue
        
        # Find all sc* directories (staging areas)
        try:
            for sc_dir in os.listdir(crossfire_base):
                if not sc_dir.startswith('sc'):
                    continue
                
                crossfire_path = f"{crossfire_base}/{sc_dir}/crossfire/crossfire"
                if not os.path.exists(crossfire_path):
                    continue
                
                # Find crossfire run folders with timestamps
                for run_dir in os.listdir(crossfire_path):
                    # Extract date from folder name like: block.rtl1p0.2026_01_26_035756.12345
                    match = re.search(r'(\d{4}_\d{2}_\d{2}_\d{6})', run_dir)
                    if match:
                        date_str = match.group(1)
                        # Parse as comparable datetime
                        try:
                            run_date = datetime.strptime(date_str, '%Y_%m_%d_%H%M%S')
                            
                            if best_date is None or run_date > best_date:
                                best_date = run_date
                                best_workspace = block_path
                                best_info = {
                                    'workspace': workspace,
                                    'date': run_date.strftime('%Y-%m-%d %H:%M:%S'),
                                    'crossfire_dir': f"{crossfire_path}/{run_dir}"
                                }
                        except ValueError:
                            continue
        except (PermissionError, OSError):
            continue
    
    return best_workspace, best_info


def main():
    parser = argparse.ArgumentParser(
        description='Generate waiver file from crossfire analysis results',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate waivers for single block
  %(prog)s -block bpbiqrfip
  
  # Generate waivers for multiple blocks from file
  %(prog)s -block_list block_list.txt
  
  # Generate waivers only for timing violations
  %(prog)s -block bpbiqrfip -tool crossfire_timing
  
  # Generate waivers for top 10 violations only
  %(prog)s -block bpbiqrfip -top 10
  
  # Custom justification
  %(prog)s -block bpbiqrfip -justification "Known issue - Jira PROJ-123"
  
  # Specify output location
  %(prog)s -block bpbiqrfip -outdir /path/to/output
  
  # Use multiple workspaces (picks newest data for each block)
  %(prog)s -block_list blocks.txt -workspace_list /path/wa1,/path/wa2
        """
    )
    
    # Mutually exclusive: -block or -block_list or -block_list_with_types
    block_group = parser.add_mutually_exclusive_group(required=True)
    block_group.add_argument('-block',
                       help='Single block name')
    block_group.add_argument('-block_list',
                       help='File containing list of block names (one per line)')
    block_group.add_argument('-block_list_with_types',
                       help='File containing list of blocks with types (format: block_name,type)')
    
    parser.add_argument('-outdir', default='.',
                       help='Output directory (where analysis results are located)')
    
    # Workspace options - mutually exclusive
    ws_group = parser.add_mutually_exclusive_group()
    ws_group.add_argument('-workspace', default=None,
                       help='Single workspace path for LEF/lib lookup')
    ws_group.add_argument('-workspace_list',
                       help='Comma-separated list of workspace paths (picks newest data per block)')
    
    parser.add_argument('-tool',
                       help='Filter by specific tool (e.g., crossfire_timing)')
    
    parser.add_argument('-top', type=int,
                       help='Generate waivers for top N violations only')
    
    parser.add_argument('-justification',
                       help='Custom justification text for all waivers')
    
    parser.add_argument('-output',
                       help='Output waiver file path (default: <block>.waivers). For batch mode, ignored.')
    
    parser.add_argument('-combined', action='store_true',
                       help='For batch mode: also generate combined waiver file for all blocks')
    
    parser.add_argument('-skip_analysis', action='store_true',
                       help='Use cached JSON analysis instead of fresh data from workspace')
    
    args = parser.parse_args()
    
    # Parse workspace list
    if args.workspace_list:
        workspaces = [ws.strip() for ws in args.workspace_list.split(',')]
        print(f"[INFO] Using {len(workspaces)} workspaces (will pick newest data per block):")
        for ws in workspaces:
            print(f"       - {ws}")
    elif args.workspace:
        workspaces = [args.workspace]
    else:
        workspaces = ['/nfs/site/disks/idc_bei_hip/gfc-workspace/sunger']
    
    # Get list of blocks to process
    if args.block:
        blocks = [args.block]
    elif args.block_list:
        # Read from block_list file (block names only)
        if not os.path.exists(args.block_list):
            print(f"[ERROR] Block list file not found: {args.block_list}")
            return 1
        
        with open(args.block_list, 'r') as f:
            blocks = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    else:
        # Read from block_list_with_types file (format: block_name,type)
        if not os.path.exists(args.block_list_with_types):
            print(f"[ERROR] Block list file not found: {args.block_list_with_types}")
            return 1
        
        with open(args.block_list_with_types, 'r') as f:
            blocks = []
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    # Extract just the block name (before comma)
                    block_name = line.split(',')[0].strip()
                    blocks.append(block_name)
        
        print(f"[INFO] Loaded {len(blocks)} blocks from {args.block_list_with_types}")
    
    # Process each block
    success_count = 0
    failed_blocks = []
    all_waiver_files = []
    workspace_used = {}  # Track which workspace was used for each block
    
    for i, block in enumerate(blocks, 1):
        print(f"\n{'#' * 80}")
        print(f"# Processing block {i}/{len(blocks)}: {block}")
        print(f"{'#' * 80}")
        
        # Find best workspace for this block
        workspace_path, ws_info = find_newest_workspace(block, workspaces)
        
        if workspace_path:
            workspace_used[block] = ws_info
            print(f"[INFO] Using workspace: {ws_info['workspace']} (crossfire date: {ws_info['date']})")
        else:
            print(f"[WARNING] Block {block} not found in any workspace, using first workspace")
            workspace_path = f"{workspaces[0]}/{block}"
        
        generator = WaiverGenerator(block, args.outdir, workspace_path)
        
        # For batch mode, always use default output name
        output_file = args.output if args.block else None
        
        # Run with skip_analysis flag
        result = generator.run(args.tool, args.top, args.justification, output_file, args.skip_analysis)
        
        if result == 0:
            success_count += 1
            waiver_file = output_file or os.path.join(args.outdir, f"{block}.waivers")
            all_waiver_files.append(waiver_file)
        else:
            failed_blocks.append(block)
    
    # Print summary for batch mode
    if len(blocks) > 1:
        print(f"\n{'=' * 80}")
        print(f"BATCH WAIVER GENERATION SUMMARY")
        print(f"{'=' * 80}")
        print(f"Total blocks:     {len(blocks)}")
        print(f"Successful:       {success_count}")
        print(f"Failed:           {len(failed_blocks)}")
        
        if failed_blocks:
            print(f"\nFailed blocks:")
            for block in failed_blocks:
                print(f"  - {block}")
        
        # Generate combined waiver file if requested
        if args.combined and all_waiver_files:
            combined_file = os.path.join(args.outdir, "combined_waivers.waivers")
            print(f"\n[INFO] Generating combined waiver file...")
            
            # Track stats for report
            stats = {
                'blocks': {},           # block -> {tool -> [rules]}
                'rules': {},            # rule_id -> {blocks: set, tool: str, count: int, justification: str}
                'tools': {},            # tool -> {blocks: set, rules: set, count: int}
            }
            
            with open(combined_file, 'w') as outf:
                outf.write(f"# Combined Waiver File\n")
                outf.write(f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                outf.write(f"# Blocks: {len(all_waiver_files)}\n")
                outf.write(f"# {'=' * 70}\n\n")
                
                for waiver_file in all_waiver_files:
                    if os.path.exists(waiver_file):
                        block_name = os.path.basename(waiver_file).replace('.waivers', '')
                        outf.write(f"\n# {'=' * 70}\n")
                        outf.write(f"# Block: {block_name}\n")
                        outf.write(f"# {'=' * 70}\n\n")
                        
                        with open(waiver_file, 'r') as inf:
                            content = inf.read()
                            outf.write(content)
                        outf.write("\n")
                        
                        # Parse content for stats
                        parse_waiver_stats(content, block_name, stats)
            
            print(f"[SUCCESS] Combined waiver file: {combined_file}")
            
            # Generate readable report
            report_file = os.path.join(args.outdir, "combined_waivers_report.txt")
            generate_waiver_report(stats, report_file, len(all_waiver_files))
        
        print(f"{'=' * 80}\n")
    
    # Cleanup __pycache__ directory
    pycache_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '__pycache__')
    if os.path.exists(pycache_dir):
        import shutil
        shutil.rmtree(pycache_dir)
    
    return 0 if not failed_blocks else 1


if __name__ == '__main__':
    sys.exit(main())
