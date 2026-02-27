#!/usr/bin/env python3
"""
Backup Utility - Create compressed backups of directories or files.

This script creates timestamped compressed archives of specified directories or files,
with options for compression format and backup rotation.
"""

import os
import sys
import shutil
import argparse
from pathlib import Path
from datetime import datetime
import tarfile
import zipfile


def create_backup(source, destination, format='tar.gz', max_backups=5):
    """Create a compressed backup of the source."""
    source_path = Path(source)
    dest_path = Path(destination)
    
    if not source_path.exists():
        print(f"Error: Source {source} does not exist")
        return False
    
    # Create destination directory if it doesn't exist
    dest_path.mkdir(parents=True, exist_ok=True)
    
    # Generate backup filename with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    source_name = source_path.name
    
    if format == 'zip':
        backup_name = f"{source_name}_backup_{timestamp}.zip"
        backup_path = dest_path / backup_name
        
        print(f"Creating ZIP backup: {backup_path}")
        with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            if source_path.is_file():
                zipf.write(source_path, source_path.name)
            else:
                for root, dirs, files in os.walk(source_path):
                    for file in files:
                        file_path = Path(root) / file
                        arcname = file_path.relative_to(source_path.parent)
                        zipf.write(file_path, arcname)
    else:
        # Default to tar.gz
        backup_name = f"{source_name}_backup_{timestamp}.tar.gz"
        backup_path = dest_path / backup_name
        
        print(f"Creating TAR.GZ backup: {backup_path}")
        with tarfile.open(backup_path, 'w:gz') as tar:
            tar.add(source_path, arcname=source_path.name)
    
    print(f"Backup created successfully: {backup_path}")
    print(f"Backup size: {backup_path.stat().st_size / (1024*1024):.2f} MB")
    
    # Rotate old backups
    rotate_backups(dest_path, source_name, max_backups)
    
    return True


def rotate_backups(backup_dir, source_name, max_backups):
    """Remove old backups, keeping only the most recent max_backups."""
    if max_backups <= 0:
        return
    
    # Find all backup files for this source
    pattern = f"{source_name}_backup_*"
    backups = sorted(backup_dir.glob(pattern), key=lambda p: p.stat().st_mtime)
    
    # Remove oldest backups if we exceed max_backups
    if len(backups) > max_backups:
        for old_backup in backups[:-max_backups]:
            print(f"Removing old backup: {old_backup.name}")
            old_backup.unlink()


def main():
    parser = argparse.ArgumentParser(
        description='Create compressed backups of directories or files'
    )
    parser.add_argument(
        'source',
        help='Source directory or file to backup'
    )
    parser.add_argument(
        'destination',
        help='Destination directory for backups'
    )
    parser.add_argument(
        '-f', '--format',
        choices=['tar.gz', 'zip'],
        default='tar.gz',
        help='Backup format (default: tar.gz)'
    )
    parser.add_argument(
        '-m', '--max-backups',
        type=int,
        default=5,
        help='Maximum number of backups to keep (0 for unlimited, default: 5)'
    )
    
    args = parser.parse_args()
    
    print(f"Source: {args.source}")
    print(f"Destination: {args.destination}")
    print(f"Format: {args.format}")
    print("-" * 50)
    
    success = create_backup(
        args.source,
        args.destination,
        format=args.format,
        max_backups=args.max_backups
    )
    
    if not success:
        sys.exit(1)


if __name__ == '__main__':
    main()
