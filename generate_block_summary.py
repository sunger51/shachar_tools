#!/usr/bin/env python3
"""
Generate Block Error Summary Reports
====================================

SCRIPT TYPE: STANDALONE (does not call other scripts)

DEPENDENCIES:
    - None (reads data files created by generate_waivers.py)
    - openpyxl (optional, for Excel output)

DESCRIPTION:
    Creates summary reports from crossfire violation data. This script:
    1. Reads violation CSV files from each block's analysis directory
    2. Aggregates error counts by block and rule
    3. Generates summary reports in multiple formats

INPUTS:
    - Data directory (-d): Contains {block}_detailed/ folders with analysis results
    - Block list file (-b): File with block names and types (block_name,type)

OUTPUTS (all created in the -d directory):
    - block_error_summary.txt      : Human-readable summary
    - block_error_summary.csv      : Pivot table (one column per rule)
    - block_error_combined_raw.csv : All raw violation data combined
    - block_error_summary.xlsx     : Excel workbook with Summary and Raw Data sheets

USAGE:
    # Generate all reports
    python3 generate_block_summary.py -d update_rules -b block_list_with_types.txt
    
    # Skip Excel generation
    python3 generate_block_summary.py -d update_rules -b block_list_with_types.txt --no-xlsx
    
    # Generate and email report
    python3 generate_block_summary.py -d update_rules -b block_list_with_types.txt -m user@intel.com

OPTIONS:
    -d, --dir DIR      : Path to directory containing block analysis data (required)
    -b, --blocks FILE  : Path to block list file with types (required)
    -x, --xlsx         : Generate Excel file (default: enabled)
    --no-xlsx          : Skip Excel file generation
    -m, --mail EMAIL   : Email address to send the xlsx report to

Author: Block Summary Generator
Date: February 2026
"""

import os
import re
import csv
import argparse
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
from collections import defaultdict

def load_block_types(block_list_file):
    """Load block names and their types from block list file"""
    block_types = {}
    with open(block_list_file, 'r') as f:
        for line in f:
            line = line.strip()
            if ',' in line:
                parts = line.split(',')
                block_name = parts[0].strip()
                block_type = parts[1].strip()
                block_types[block_name] = block_type
    return block_types

def parse_csv_file(csv_file):
    """Parse a CSV violations file and extract rules (errors)"""
    errors = defaultdict(int)
    
    with open(csv_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            rule_id = row.get('Rule_ID', '')
            # Extract just the rule number (before the colon)
            if ':' in rule_id:
                rule_id = rule_id.split(':')[0]
            failures = int(row.get('Failures', 0))
            if rule_id:
                errors[rule_id] += failures
    
    return dict(errors)

def generate_csv(data_dir, block_list_file):
    """Generate CSV version of the summary with one column per rule"""
    block_types = load_block_types(block_list_file)
    
    block_data = []
    all_rules = set()
    
    for block_name, block_type in block_types.items():
        csv_file = os.path.join(data_dir, f"{block_name}_detailed", f"{block_name}_crossfire_violations.csv")
        errors = {}
        total_errors = 0
        if os.path.exists(csv_file):
            errors = parse_csv_file(csv_file)
            total_errors = sum(errors.values())
            all_rules.update(errors.keys())
        block_data.append({
            'name': block_name,
            'type': block_type,
            'errors': errors,
            'total': total_errors
        })
    
    block_data.sort(key=lambda x: (x['type'], x['name']))
    all_rules = sorted(all_rules)
    
    csv_output = os.path.join(data_dir, "block_error_summary.csv")
    with open(csv_output, 'w') as f:
        # Header: Block Name, Type, Total Errors, then one column per rule
        header = ["Block Name", "Type", "Total Errors"] + all_rules
        f.write(",".join([f'"{h}"' for h in header]) + "\n")
        
        for block in block_data:
            row = [block['name'], block['type'], str(block['total'])]
            for rule in all_rules:
                row.append(str(block['errors'].get(rule, 0)))
            f.write(",".join(row) + "\n")
    
    print(f"CSV written to: {csv_output}")

def generate_combined_raw_csv(data_dir, block_list_file):
    """Generate CSV with all raw violation data combined from all blocks"""
    block_types = load_block_types(block_list_file)
    
    combined_output = os.path.join(data_dir, "block_error_combined_raw.csv")
    first_file = True
    
    with open(combined_output, 'w') as outfile:
        for block_name in sorted(block_types.keys()):
            csv_file = os.path.join(data_dir, f"{block_name}_detailed", f"{block_name}_crossfire_violations.csv")
            if os.path.exists(csv_file):
                with open(csv_file, 'r') as infile:
                    lines = infile.readlines()
                    if first_file:
                        # Write header from first file
                        outfile.writelines(lines)
                        first_file = False
                    else:
                        # Skip header for subsequent files
                        outfile.writelines(lines[1:])
    
    print(f"Combined raw CSV written to: {combined_output}")

def generate_xlsx(data_dir, block_list_file):
    """Generate Excel file with both summary and raw data sheets"""
    try:
        import openpyxl
    except ImportError:
        print("Error: openpyxl not installed. Install with: pip install openpyxl")
        return
    
    block_types = load_block_types(block_list_file)
    
    # Collect block data
    block_data = []
    all_rules = set()
    
    for block_name, block_type in block_types.items():
        csv_file = os.path.join(data_dir, f"{block_name}_detailed", f"{block_name}_crossfire_violations.csv")
        errors = {}
        total_errors = 0
        if os.path.exists(csv_file):
            errors = parse_csv_file(csv_file)
            total_errors = sum(errors.values())
            all_rules.update(errors.keys())
        block_data.append({
            'name': block_name,
            'type': block_type,
            'errors': errors,
            'total': total_errors
        })
    
    block_data.sort(key=lambda x: (x['type'], x['name']))
    all_rules = sorted(all_rules)
    
    # Create workbook
    wb = openpyxl.Workbook()
    
    # Sheet 1: Summary
    ws_summary = wb.active
    ws_summary.title = "Summary"
    
    header = ["Block Name", "Type", "Total Errors"] + all_rules
    ws_summary.append(header)
    
    for block in block_data:
        row = [block['name'], block['type'], block['total']]
        for rule in all_rules:
            row.append(block['errors'].get(rule, 0))
        ws_summary.append(row)
    
    # Sheet 2: Raw Data
    ws_raw = wb.create_sheet("Raw Data")
    first_file = True
    
    for block_name in sorted(block_types.keys()):
        csv_file = os.path.join(data_dir, f"{block_name}_detailed", f"{block_name}_crossfire_violations.csv")
        if os.path.exists(csv_file):
            with open(csv_file, 'r') as f:
                reader = csv.reader(f)
                for i, row in enumerate(reader):
                    if first_file or i > 0:  # Include header only from first file
                        ws_raw.append(row)
                first_file = False
    
    # Save workbook
    xlsx_output = os.path.join(data_dir, "block_error_summary.xlsx")
    wb.save(xlsx_output)
    print(f"Excel file written to: {xlsx_output}")
    return xlsx_output

def get_user_email():
    """Get user's Intel email address from system"""
    import subprocess
    user = os.environ.get('USER', '')
    try:
        # Get full name from passwd (format: firstname.lastname,employeeid)
        result = subprocess.run(['getent', 'passwd', user], capture_output=True, text=True)
        if result.returncode == 0:
            gecos = result.stdout.strip().split(':')[4]  # GECOS field
            if ',' in gecos:
                full_name = gecos.split(',')[0]  # firstname.lastname
                return full_name + '@intel.com'
    except Exception:
        pass
    # Fallback to username@intel.com
    return user + '@intel.com'

def send_email(recipient, xlsx_file):
    """Send email with xlsx file attached"""
    # If recipient is 'auto' or doesn't have @, look up email
    if recipient == '$USER' or (recipient and '@' not in recipient):
        recipient = get_user_email()
    
    sender = get_user_email()
    
    msg = MIMEMultipart()
    msg['From'] = sender
    msg['To'] = recipient
    msg['Subject'] = 'Block Error Summary Report'
    
    body = 'Please find attached the Block Error Summary report.\n\nThis email was automatically generated.'
    msg.attach(MIMEText(body, 'plain'))
    
    # Attach xlsx file
    with open(xlsx_file, 'rb') as f:
        part = MIMEBase('application', 'vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f'attachment; filename="{os.path.basename(xlsx_file)}"')
        msg.attach(part)
    
    try:
        smtp = smtplib.SMTP('localhost')
        smtp.sendmail(sender, recipient, msg.as_string())
        smtp.quit()
        print(f"Email sent to: {recipient}")
    except Exception as e:
        print(f"Error sending email: {e}")

def main():
    parser = argparse.ArgumentParser(description='Generate block error summary from violation CSV files.')
    parser.add_argument('-d', '--dir', required=True, help='Path to directory containing block data')
    parser.add_argument('-b', '--blocks', required=True, help='Path to block list file (block_name,type)')
    parser.add_argument('-x', '--xlsx', action='store_true', default=True, help='Generate Excel file (default: enabled)')
    parser.add_argument('--no-xlsx', action='store_false', dest='xlsx', help='Skip Excel file generation')
    parser.add_argument('-m', '--mail', help='Email address to send the xlsx report to')
    args = parser.parse_args()
    
    data_dir = args.dir
    block_list_file = args.blocks
    
    block_types = load_block_types(block_list_file)
    
    # Collect data for each block
    block_data = []
    
    for block_name, block_type in block_types.items():
        csv_file = os.path.join(data_dir, f"{block_name}_detailed", f"{block_name}_crossfire_violations.csv")
        
        errors = {}
        total_errors = 0
        
        if os.path.exists(csv_file):
            errors = parse_csv_file(csv_file)
            total_errors = sum(errors.values())
        
        block_data.append({
            'name': block_name,
            'type': block_type,
            'errors': errors,
            'total': total_errors
        })
    
    # Sort by type, then by name
    block_data.sort(key=lambda x: (x['type'], x['name']))
    
    # Output file in data directory
    output_file = os.path.join(data_dir, "block_error_summary.txt")
    
    # Generate output
    with open(output_file, 'w') as f:
        f.write("=" * 100 + "\n")
        f.write("BLOCK ERROR SUMMARY TABLE\n")
        f.write(f"Generated from waiver files in {data_dir}/ directory\n")
        f.write("=" * 100 + "\n\n")
        
        # Summary by type
        f.write("SUMMARY BY BLOCK TYPE\n")
        f.write("-" * 50 + "\n")
        f.write(f"{'Type':<15} {'Blocks':<10} {'Total Errors':<15}\n")
        f.write("-" * 50 + "\n")
        
        type_summary = defaultdict(lambda: {'count': 0, 'errors': 0})
        for block in block_data:
            type_summary[block['type']]['count'] += 1
            type_summary[block['type']]['errors'] += block['total']
        
        for btype in sorted(type_summary.keys()):
            f.write(f"{btype:<15} {type_summary[btype]['count']:<10} {type_summary[btype]['errors']:<15}\n")
        
        grand_total = sum(b['total'] for b in block_data)
        f.write("-" * 50 + "\n")
        f.write(f"{'TOTAL':<15} {len(block_data):<10} {grand_total:<15}\n")
        f.write("\n")
        
        # Detailed table - one block per section for full visibility
        f.write("=" * 100 + "\n")
        f.write("DETAILED BLOCK TABLE\n")
        f.write("=" * 100 + "\n\n")
        
        current_type = None
        for block in block_data:
            if block['type'] != current_type:
                current_type = block['type']
                f.write("-" * 100 + "\n")
                f.write(f"TYPE: {current_type}\n")
                f.write("-" * 100 + "\n")
            
            f.write(f"\n  Block: {block['name']}\n")
            f.write(f"  Total Errors: {block['total']}\n")
            if block['errors']:
                error_list = [f"{rule}:{count}" for rule, count in sorted(block['errors'].items())]
                f.write(f"  Error Rules: {', '.join(error_list)}\n")
            else:
                f.write(f"  Error Rules: (none - no waiver file found)\n")
        
        f.write("\n")
        f.write("=" * 100 + "\n")
        f.write(f"Total Blocks: {len(block_data)}\n")
        f.write(f"Total Errors (waivers): {grand_total}\n")
        f.write("=" * 100 + "\n")
    
    print(f"Summary written to: {output_file}")
    generate_csv(data_dir, block_list_file)
    generate_combined_raw_csv(data_dir, block_list_file)
    
    xlsx_file = None
    if args.xlsx:
        xlsx_file = generate_xlsx(data_dir, block_list_file)
    
    if args.mail:
        if xlsx_file:
            send_email(args.mail, xlsx_file)
        else:
            print("Error: Cannot send email without xlsx file. Remove --no-xlsx option.")

if __name__ == "__main__":
    main()
