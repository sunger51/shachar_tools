#!/usr/bin/env python3
"""
File Organizer - Organize files in a directory by extension or date.

This script helps organize cluttered directories by moving files into 
subdirectories based on their file extensions or modification dates.
"""

import os
import sys
import shutil
import argparse
from pathlib import Path
from datetime import datetime


def organize_by_extension(directory):
    """Organize files by their extensions."""
    directory = Path(directory)
    
    if not directory.exists():
        print(f"Error: Directory {directory} does not exist")
        return False
    
    files = [f for f in directory.iterdir() if f.is_file()]
    
    for file in files:
        # Skip hidden files
        if file.name.startswith('.'):
            continue
            
        extension = file.suffix[1:] if file.suffix else 'no_extension'
        
        # Create subdirectory for this extension
        target_dir = directory / extension
        target_dir.mkdir(exist_ok=True)
        
        # Move file
        target_path = target_dir / file.name
        
        # Handle name conflicts
        counter = 1
        while target_path.exists():
            stem = file.stem
            target_path = target_dir / f"{stem}_{counter}{file.suffix}"
            counter += 1
        
        shutil.move(str(file), str(target_path))
        print(f"Moved: {file.name} -> {extension}/{target_path.name}")
    
    return True


def organize_by_date(directory):
    """Organize files by their modification date (Year/Month format)."""
    directory = Path(directory)
    
    if not directory.exists():
        print(f"Error: Directory {directory} does not exist")
        return False
    
    files = [f for f in directory.iterdir() if f.is_file()]
    
    for file in files:
        # Skip hidden files
        if file.name.startswith('.'):
            continue
        
        # Get modification time
        mod_time = datetime.fromtimestamp(file.stat().st_mtime)
        date_folder = mod_time.strftime('%Y/%m_%B')
        
        # Create subdirectory for this date
        target_dir = directory / date_folder
        target_dir.mkdir(parents=True, exist_ok=True)
        
        # Move file
        target_path = target_dir / file.name
        
        # Handle name conflicts
        counter = 1
        while target_path.exists():
            stem = file.stem
            target_path = target_dir / f"{stem}_{counter}{file.suffix}"
            counter += 1
        
        shutil.move(str(file), str(target_path))
        print(f"Moved: {file.name} -> {date_folder}/{target_path.name}")
    
    return True


def main():
    parser = argparse.ArgumentParser(
        description='Organize files in a directory by extension or date'
    )
    parser.add_argument(
        'directory',
        help='Directory to organize'
    )
    parser.add_argument(
        '-m', '--mode',
        choices=['extension', 'date'],
        default='extension',
        help='Organization mode: extension or date (default: extension)'
    )
    
    args = parser.parse_args()
    
    print(f"Organizing files in: {args.directory}")
    print(f"Mode: {args.mode}")
    print("-" * 50)
    
    if args.mode == 'extension':
        success = organize_by_extension(args.directory)
    else:
        success = organize_by_date(args.directory)
    
    if success:
        print("-" * 50)
        print("Organization complete!")
    else:
        sys.exit(1)


if __name__ == '__main__':
    main()
