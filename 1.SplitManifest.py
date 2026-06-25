import os
import re

metadata_file = "./RealManifests/metadata-6.tsv"
manifest_file = "./RealManifests/manifest-7.tsv"
new_manifest_dir = "sub_manifests"

os.makedirs(new_manifest_dir, exist_ok=True)

# ------------------------------------------------------------------------------
# STEP 1: Parse Metadata file by sample_id
# ------------------------------------------------------------------------------
metadata_lookup = {}

with open(metadata_file, "r") as f:
    meta_lines = f.readlines()

meta_header = meta_lines[0]
meta_delimiter = "\t" if "\t" in meta_header else ","
meta_header_fields = [field.strip() for field in meta_header.split(meta_delimiter)]

try:
    meta_sample_idx = meta_header_fields.index("sample.sample_id")
    meta_subject_idx = meta_header_fields.index("subject.source_subject_id")
    meta_timepoint_idx = meta_header_fields.index("sample.timepoint_sequential")
except ValueError as e:
    # Fallback to check for un-prefixed "sample_id" if needed
    try:
        meta_sample_idx = meta_header_fields.index("sample_id")
    except ValueError:
        raise ValueError(f"Could not find sample_id column in metadata header: {e}")

for row in meta_lines[1:]:
    if not row.strip():
        continue
    fields = row.split(meta_delimiter)
    if len(fields) <= max(meta_sample_idx, meta_subject_idx, meta_timepoint_idx):
        continue
    
    # Grab data fields
    s_id = fields[meta_sample_idx].strip()
    sub_id = fields[meta_subject_idx].strip()
    tp_seq = fields[meta_timepoint_idx].strip()
    
    # Map by sample_id
    metadata_lookup[s_id] = {
        "subject_id": sub_id,
        "timepoint": tp_seq
    }

# ------------------------------------------------------------------------------
# STEP 2: Process Operational Manifest & Match on sample_id
# ------------------------------------------------------------------------------
with open(manifest_file, "r") as f:
    manifest_lines = f.readlines()

manifest_header = manifest_lines[0]
manifest_delimiter = "\t" if "\t" in manifest_header else ","
manifest_header_fields = [field.strip() for field in manifest_header.split(manifest_delimiter)]

try:
    manifest_file_id_idx = manifest_header_fields.index("file_id")
    manifest_sample_idx = manifest_header_fields.index("sample_id")
except ValueError as e:
    raise ValueError(f"Missing essential infrastructure columns in manifest header: {e}")

files_created = 0
missing_metadata_count = 0

for row in manifest_lines[1:]:
    if not row.strip():
        continue
    
    fields = row.split(manifest_delimiter)
    if len(fields) <= max(manifest_file_id_idx, manifest_sample_idx):
        continue
        
    file_id = fields[manifest_file_id_idx].strip()
    manifest_sample_id = fields[manifest_sample_idx].strip()
    
    # Extract the first sample ID if it's a comma-separated list
    clean_sample_key = manifest_sample_id.split(",")[0].strip()
    
    # Match using the common sample_id key
    if clean_sample_key in metadata_lookup:
        subject_source = metadata_lookup[clean_sample_key]["subject_id"]
        timepoint = metadata_lookup[clean_sample_key]["timepoint"]
    else:
        missing_metadata_count += 1
        subject_source = "UNKNOWN"
        timepoint = "UNKNOWN"

    # Construct the descriptive directory naming sequence
    combined_name = f"{file_id}_subject.source_subject_id_{subject_source}_sample.timepoint_sequential_{timepoint}"
    combined_name = re.sub(r'[^a-zA-Z0-9_\-.]', '_', combined_name)
    
    # Build target directories
    sub_dir_path = os.path.join(new_manifest_dir, combined_name)
    os.makedirs(sub_dir_path, exist_ok=True)

    # Output manifest path
    output_filename = f"{combined_name}.txt"
    full_output_path = os.path.join(sub_dir_path, output_filename)

    # Write out operational structure columns safely
    with open(full_output_path, "w") as out_f:
        out_f.write(manifest_header)
        out_f.write(row)
    
    files_created += 1

print(f"Successfully generated {files_created} operational sub-manifests inside '{new_manifest_dir}'.")
if missing_metadata_count > 0:
    print(f"Warning: {missing_metadata_count} sample entries couldn't find matching metadata rows.")
