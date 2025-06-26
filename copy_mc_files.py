#!/usr/bin/env python3
"""
Script to copy qn_mc.txt files from synthetic_dataset_2 to synthetic_dataset_2_3
"""

import os
import shutil
from pathlib import Path

def copy_mc_files():
    # Define source and destination directories
    source_dir = Path("../../synthetic_dataset_2")
    dest_dir = Path("../../synthetic_dataset_2_3")
    
    # Check if directories exist
    if not source_dir.exists():
        print(f"Error: Source directory {source_dir} does not exist")
        return
    
    if not dest_dir.exists():
        print(f"Error: Destination directory {dest_dir} does not exist")
        return
    
    # Get all q folders from source directory
    q_folders = [f for f in source_dir.iterdir() if f.is_dir() and f.name.startswith('q')]
    
    copied_count = 0
    failed_count = 0
    
    print(f"Found {len(q_folders)} q folders in source directory")
    
    for q_folder in sorted(q_folders):
        q_name = q_folder.name
        source_mc_file = q_folder / f"{q_name}_mc.txt"
        dest_q_folder = dest_dir / q_name
        dest_mc_file = dest_q_folder / f"{q_name}_mc.txt"
        
        # Check if source mc file exists
        if not source_mc_file.exists():
            print(f"Warning: {source_mc_file} does not exist, skipping")
            failed_count += 1
            continue
        
        # Check if destination q folder exists
        if not dest_q_folder.exists():
            print(f"Warning: Destination folder {dest_q_folder} does not exist, skipping")
            failed_count += 1
            continue
        
        try:
            # Copy the file
            shutil.copy2(source_mc_file, dest_mc_file)
            print(f"Copied: {source_mc_file} -> {dest_mc_file}")
            copied_count += 1
        except Exception as e:
            print(f"Error copying {source_mc_file}: {e}")
            failed_count += 1
    
    print(f"\nSummary:")
    print(f"Successfully copied: {copied_count} files")
    print(f"Failed: {failed_count} files")

if __name__ == "__main__":
    copy_mc_files() 