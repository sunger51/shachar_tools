#!/usr/bin/env /usr/intel/bin/python3
"""
Crossfire Detailed Analyzer
===========================

SCRIPT TYPE: HELPER (called by generate_waivers.py, not typically run standalone)

DEPENDENCIES:
    - None (standalone module)

DESCRIPTION:
    Parses crossfire workspace results and extracts violation data. This script:
    1. Finds crossfire review directory in workspace
    2. Parses .finale.csv and .violations.xml files
    3. Extracts rule IDs, failure counts, and sample error messages
    4. Generates JSON analysis file and CSV violation report

CALLED BY:
    - generate_waivers.py (imports DetailedCrossfireAnalyzer class)

INPUTS:
    - Workspace path: Directory containing crossfire results
    - Block name: Name of the block to analyze

OUTPUTS (created in output_dir/{block}_detailed/):
    - {block}_detailed_analysis.json : Structured analysis results
    - {block}_crossfire_violations.csv : Flat CSV of all violations

STANDALONE USAGE (for debugging):
    python3 analyze_crossfire_detailed.py  # (no CLI, import as module)
    
    # From Python:
    from analyze_crossfire_detailed import DetailedCrossfireAnalyzer
    analyzer = DetailedCrossfireAnalyzer('blockname', 'outdir', '/path/to/workspace')
    analyzer.analyze()

Author: Crossfire Analysis Tool
Date: February 2026
"""

import os
import re
import csv
import json
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
import glob as glob_module


class DetailedCrossfireAnalyzer:
    """Analyze crossfire results and generate detailed violation reports."""
    
    def __init__(self, block_name, output_dir, workspace_path):
        self.block_name = block_name
        self.output_dir = output_dir
        self.workspace_path = workspace_path
        self.results = {
            'block': block_name,
            'timestamp': datetime.now().isoformat(),
            'tools': {},
            'summary': {
                'total_violations': 0,
                'total_waived': 0,
                'total_approved': 0
            }
        }
    
    def find_crossfire_dir(self):
        """Find the crossfire results directory in workspace."""
        # Try different possible paths
        patterns = [
            f"{self.workspace_path}/{self.block_name}/ship/ip/{self.block_name}/latest/crossfire/review",
            f"{self.workspace_path}/{self.block_name}/ship/ip/{self.block_name}/*/crossfire/review",
            f"{self.workspace_path}/ship/ip/{self.block_name}/latest/crossfire/review",
            f"{self.workspace_path}/ship/ip/{self.block_name}/*/crossfire/review",
        ]
        
        for pattern in patterns:
            matches = glob_module.glob(pattern)
            if matches:
                # Return the newest one
                matches.sort(key=os.path.getmtime, reverse=True)
                return matches[0]
        
        return None
    
    def parse_finale_csv(self, csv_file):
        """Parse the finale.csv file for summary data."""
        violations = []
        
        with open(csv_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                tool = row.get('tool', '')
                check = row.get('check', '')
                status = row.get('status', '').strip()
                fail_cnt = int(row.get('fail_cnt', 0) or 0)
                waive_cnt = int(row.get('waive_cnt', 0) or 0)
                approv_cnt = int(row.get('approv_cnt', 0) or 0)
                unique_id = row.get('unique_id', '')
                bucket = row.get('bucket', 'none')
                
                if fail_cnt > 0 or waive_cnt > 0:
                    violations.append({
                        'tool': tool,
                        'check': check,
                        'status': status,
                        'failures': fail_cnt,
                        'waived': waive_cnt,
                        'approved': approv_cnt,
                        'rule_id': unique_id,
                        'bucket': bucket
                    })
        
        return violations
    
    def parse_violations_xml(self, xml_file, tool_name):
        """Parse violations XML file for detailed error messages."""
        violations = []
        
        try:
            tree = ET.parse(xml_file)
            root = tree.getroot()
            
            for check in root.findall('.//check'):
                uniq_id = check.findtext('uniq_id', '')
                description = check.findtext('description', '')
                
                # Get fail elements for sample errors
                fails = check.findall('.//fail')
                sample_errors = []
                for fail in fails[:5]:  # Get up to 5 sample errors
                    sample_errors.append(fail.text.strip() if fail.text else '')
                
                # Count failures
                fail_count = len(fails)
                indicator = check.findtext('indicator', '0')
                try:
                    indicator = int(indicator)
                except:
                    indicator = 0
                
                if fail_count > 0 or indicator > 0:
                    violations.append({
                        'rule_id': uniq_id,
                        'description': description,
                        'failures': fail_count if fail_count > 0 else indicator,
                        'sample_errors': sample_errors,
                        'tool': tool_name
                    })
        except ET.ParseError as e:
            print(f"[WARNING] Error parsing XML {xml_file}: {e}")
        
        return violations
    
    def generate_violation_csv(self, output_file, violations):
        """Generate the crossfire_violations.csv file."""
        # Get HTML report path for reference
        review_dir = self.find_crossfire_dir()
        html_report = "N/A"
        if review_dir:
            # Try to find HTML report path
            parent_dir = os.path.dirname(review_dir)
            html_paths = glob_module.glob(f"{parent_dir}/crossfire/*/html/index_per_rule.html")
            if html_paths:
                html_report = f"firefox file://{html_paths[0]} &"
        
        with open(output_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'Block', 'Rule_ID', 'Check_Name', 'Description', 'Tool',
                'Failures', 'Waived', 'Approved', 'Bucket', 'HTML_Report', 'Sample_Error'
            ])
            
            for v in violations:
                sample_error = v.get('sample_errors', [''])[0] if v.get('sample_errors') else ''
                writer.writerow([
                    self.block_name,
                    v.get('rule_id', ''),
                    v.get('check', ''),
                    v.get('description', ''),
                    v.get('tool', ''),
                    v.get('failures', 0),
                    v.get('waived', 0),
                    v.get('approved', 0),
                    v.get('bucket', 'none'),
                    html_report,
                    sample_error
                ])
    
    def run(self):
        """Run the analysis and generate output files."""
        print(f"[INFO] Analyzing crossfire results for {self.block_name}...")
        
        # Find crossfire review directory
        review_dir = self.find_crossfire_dir()
        if not review_dir:
            print(f"[ERROR] Could not find crossfire review directory for {self.block_name}")
            print(f"[INFO] Searched in: {self.workspace_path}")
            return False
        
        print(f"[INFO] Found review directory: {review_dir}")
        
        # Create output directory
        output_detailed_dir = os.path.join(self.output_dir, f"{self.block_name}_detailed")
        os.makedirs(output_detailed_dir, exist_ok=True)
        
        # Parse finale.csv for summary
        finale_csv = os.path.join(review_dir, f"{self.block_name}.finale.csv")
        all_violations = []
        
        if os.path.exists(finale_csv):
            print(f"[INFO] Parsing {finale_csv}")
            violations = self.parse_finale_csv(finale_csv)
            all_violations.extend(violations)
            
            # Update summary
            for v in violations:
                self.results['summary']['total_violations'] += v['failures']
                self.results['summary']['total_waived'] += v['waived']
                self.results['summary']['total_approved'] += v['approved']
                
                tool = v['tool']
                if tool not in self.results['tools']:
                    self.results['tools'][tool] = {'violations': [], 'total': 0}
                self.results['tools'][tool]['violations'].append(v)
                self.results['tools'][tool]['total'] += v['failures']
        else:
            print(f"[WARNING] Finale CSV not found: {finale_csv}")
        
        # Parse violations XML files for sample errors
        xml_files = glob_module.glob(os.path.join(review_dir, f"{self.block_name}.*.violations.xml"))
        for xml_file in xml_files:
            # Extract tool name from filename
            basename = os.path.basename(xml_file)
            match = re.match(rf"{self.block_name}\.(.+)\.violations\.xml", basename)
            if match:
                tool_name = match.group(1)
                print(f"[INFO] Parsing {basename}")
                xml_violations = self.parse_violations_xml(xml_file, tool_name)
                
                # Merge sample errors into all_violations
                for xv in xml_violations:
                    for av in all_violations:
                        if av.get('rule_id') == xv.get('rule_id') and av.get('tool') == tool_name:
                            av['sample_errors'] = xv.get('sample_errors', [])
                            av['description'] = xv.get('description', av.get('description', ''))
                            break
        
        # Generate output CSV
        output_csv = os.path.join(output_detailed_dir, f"{self.block_name}_crossfire_violations.csv")
        self.generate_violation_csv(output_csv, all_violations)
        print(f"[SUCCESS] Generated: {output_csv}")
        
        # Generate JSON results for generate_waivers.py
        output_json = os.path.join(output_detailed_dir, f"{self.block_name}_detailed_analysis.json")
        with open(output_json, 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"[SUCCESS] Generated: {output_json}")
        
        print(f"[INFO] Analysis complete: {self.results['summary']['total_violations']} violations found")
        
        return True


def main():
    """Command line interface for standalone usage."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Analyze crossfire results and generate violation reports.')
    parser.add_argument('-block', required=True, help='Block name')
    parser.add_argument('-outdir', default='.', help='Output directory')
    parser.add_argument('-workspace', required=True, help='Workspace path')
    
    args = parser.parse_args()
    
    analyzer = DetailedCrossfireAnalyzer(args.block, args.outdir, args.workspace)
    success = analyzer.run()
    
    return 0 if success else 1


if __name__ == '__main__':
    import sys
    sys.exit(main())
