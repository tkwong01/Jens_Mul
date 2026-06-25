#!/bin/bash

# Target the current working directory and everything below it
TARGET_DIR="."
OUTPUT_FILE="2.manifests_absolute_paths.txt"

echo "Searching all subdirectories from $(pwd) for .txt manifest files..."
echo "--------------------------------------------------------"

# Find all .txt files, convert to absolute paths, print to screen, and save to file
# Note: Using $PWD instead of . forces find to output absolute paths.
find "$PWD" -type f -name "*gz.txt" | tee "$OUTPUT_FILE"

# Count total files found
count=$(wc -l < "$OUTPUT_FILE")
echo "--------------------------------------------------------"
echo "Total manifest files found: $count"
echo "Absolute paths saved to: $(pwd)/$OUTPUT_FILE"
