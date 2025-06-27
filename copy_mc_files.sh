#!/bin/bash

# Script to copy qn_mc.txt files from synthetic_dataset_2 to synthetic_dataset_2_3

# Define source and destination directories
SOURCE_DIR="../../synthetic_dataset_2"
DEST_DIR="../../syn"

# Check if directories exist
if [ ! -d "$SOURCE_DIR" ]; then
    echo "Error: Source directory $SOURCE_DIR does not exist"
    exit 1
fi

if [ ! -d "$DEST_DIR" ]; then
    echo "Error: Destination directory $DEST_DIR does not exist"
    exit 1
fi

# Initialize counters
copied_count=0
failed_count=0

echo "Starting to copy mc files..."

# Loop through all q folders in source directory
for source_q_folder in "$SOURCE_DIR"/q*/; do
    if [ -d "$source_q_folder" ]; then
        # Extract folder name (e.g., q1, q2, etc.)
        q_name=$(basename "$source_q_folder")
        
        # Define source and destination file paths
        source_mc_file="$source_q_folder${q_name}_mc.txt"
        dest_q_folder="$DEST_DIR/$q_name"
        dest_mc_file="$dest_q_folder/${q_name}_mc.txt"
        
        # Check if source mc file exists
        if [ ! -f "$source_mc_file" ]; then
            echo "Warning: $source_mc_file does not exist, skipping"
            ((failed_count++))
            continue
        fi
        
        # Check if destination q folder exists
        if [ ! -d "$dest_q_folder" ]; then
            echo "Warning: Destination folder $dest_q_folder does not exist, skipping"
            ((failed_count++))
            continue
        fi
        
        # Copy the file
        if cp "$source_mc_file" "$dest_mc_file"; then
            echo "Copied: $source_mc_file -> $dest_mc_file"
            ((copied_count++))
        else
            echo "Error copying $source_mc_file"
            ((failed_count++))
        fi
    fi
done

echo ""
echo "Summary:"
echo "Successfully copied: $copied_count files"
echo "Failed: $failed_count files" 