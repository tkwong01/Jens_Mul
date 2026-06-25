#!/bin/bash

# Target the sub_manifests directory
OUTPUT_FILE="2.manifests_absolute_paths.txt"

echo "Searching all subdirectories within $(pwd)/sub_manifests for .txt manifest files..."
echo "--------------------------------------------------------"

# Find all .txt files recursively, forcing absolute paths using $PWD
# ! -name protects the output file from being caught in the search
find "$PWD/sub_manifests" -type f -name "*.txt" ! -name "$OUTPUT_FILE" | tee "$OUTPUT_FILE"

# Count total files found
count=$(wc -l < "$OUTPUT_FILE")
echo "--------------------------------------------------------"
echo "Total manifest files found: $count"
echo "Absolute paths saved to: $(pwd)/$OUTPUT_FILE"
