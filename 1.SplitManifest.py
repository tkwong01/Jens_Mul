import os
import re

manifest = "./RealManifests/metadata-6.tsv"
new_manifest_dir = "sub_manifests"

# Ensure the main base directory exists
os.makedirs(new_manifest_dir, exist_ok=True)

with open(manifest, "r") as f:
    lines = f.readlines()

header = lines[0]
data_rows = lines[1:]

# Detect delimiter (Tab or Comma)
delimiter = "\t" if "\t" in header else ","

# Clean up header fields to find necessary columns
header_fields = [field.strip() for field in header.split(delimiter)]

try:
    filename_idx = header_fields.index("file.name")
    subject_idx = header_fields.index("subject.source_subject_id")
    timepoint_idx = header_fields.index("sample.timepoint_sequential")
except ValueError as e:
    raise ValueError(f"Missing required column in header: {e}")

files_created = 0

for row in data_rows:
    if not row.strip():
        continue
    
    # Split the row to extract the specific column values
    row_fields = row.split(delimiter)
    
    # Grab values and strip accidental whitespace
    base_filename = row_fields[filename_idx].strip()
    subject_source = row_fields[subject_idx].strip()
    timepoint = row_fields[timepoint_idx].strip()
    
    # Remove extension from base_filename if it's there (e.g., "sample_01.txt" -> "sample_01")
    base_name_clean = base_filename.rsplit('.', 1)[0] if '.' in base_filename else base_filename
    
    # Construct the new descriptive base name
    # e.g., "sample_01_human_TP1"
    combined_name = f"{base_name_clean}_{subject_source}_{timepoint}"
    
    # Sanitize the name to remove any spaces or weird characters that break bash/SLURM paths
    combined_name = re.sub(r'[^a-zA-Z0-9_\-.]', '_', combined_name)
    
    # Create the specific subdirectory path (e.g., sub_manifests/sample_01_human_TP1)
    sub_dir_path = os.path.join(new_manifest_dir, combined_name)
    os.makedirs(sub_dir_path, exist_ok=True)

    # Set the final file path (e.g., sub_manifests/sample_01_human_TP1/sample_01_human_TP1.txt)
    output_filename = f"{combined_name}.txt"
    full_output_path = os.path.join(sub_dir_path, output_filename)

    # Write the header and the specific row to the new file
    with open(full_output_path, "w") as out_f:
        out_f.write(header)
        out_f.write(row)
    
    files_created += 1

print(f"Successfully created {files_created} individual directories and manifest files inside '{new_manifest_dir}'.")
