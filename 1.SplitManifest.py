import os
import re

metadata_file = "./RealManifests/metadata-6.tsv"
manifest_file = "./RealManifests/manifest-7.tsv"
new_manifest_dir = "sub_manifests"

os.makedirs(new_manifest_dir, exist_ok=True)

# ------------------------------------------------------------------------------
# STEP 1: Parse Metadata file horizontally by sample_id
# ------------------------------------------------------------------------------
metadata_lookup = {}

with open(metadata_file, "r") as f:
    meta_lines = f.readlines()

meta_header = meta_lines[0].rstrip("\r\n")
meta_delimiter = "\t" if "\t" in meta_header else ","
meta_header_fields = [field.strip() for field in meta_header.split(meta_delimiter)]

try:
    meta_sample_idx = meta_header_fields.index("sample.sample_id")
    meta_subject_idx = meta_header_fields.index("subject.source_subject_id")
    meta_timepoint_idx = meta_header_fields.index("sample.timepoint_sequential")
except ValueError as e:
    try:
        meta_sample_idx = meta_header_fields.index("sample_id")
    except ValueError:
        raise ValueError(f"Could not find sample_id column in metadata header: {e}")

for row in meta_lines[1:]:
    if not row.strip():
        continue
    fields = row.rstrip("\r\n").split(meta_delimiter)
    if len(fields) <= max(meta_sample_idx, meta_subject_idx, meta_timepoint_idx):
        continue
    
    s_id = fields[meta_sample_idx].strip()
    sub_id = fields[meta_subject_idx].strip()
    tp_seq = fields[meta_timepoint_idx].strip()
    
    # Store naming attributes along with the FULL horizontal row values
    metadata_lookup[s_id] = {
        "subject_id": sub_id,
        "timepoint": tp_seq,
        "full_meta_row": meta_delimiter.join(fields)
    }

# Create a blank fallback row for unmatched metadata to keep horizontal column alignment
blank_meta_columns = meta_delimiter.join(["None"] * len(meta_header_fields))

# ------------------------------------------------------------------------------
# STEP 2: Merge Horizontally and Split into Sub-Manifests (With Adaptive Matching)
# ------------------------------------------------------------------------------
with open(manifest_file, "r") as f:
    manifest_lines = f.readlines()

manifest_header = manifest_lines[0].rstrip("\r\n")
manifest_delimiter = "\t" if "\t" in manifest_header else ","
manifest_header_fields = [field.strip() for field in manifest_header.split(manifest_delimiter)]

try:
    manifest_file_id_idx = manifest_header_fields.index("file_id")
    manifest_sample_idx = manifest_header_fields.index("sample_id")
except ValueError as e:
    raise ValueError(f"Missing essential columns in manifest header: {e}")

# Construct the master horizontal header string
merged_header = f"{manifest_header}{manifest_delimiter}{meta_header}\n"

files_created = 0

for row in manifest_lines[1:]:
    if not row.strip():
        continue
    
    fields = row.rstrip("\r\n").split(manifest_delimiter)
    if len(fields) <= max(manifest_file_id_idx, manifest_sample_idx):
        continue
        
    file_id = fields[manifest_file_id_idx].strip()
    manifest_sample_id = fields[manifest_sample_idx].strip()
    
    # 1. Grab primary key from comma-separated sequence
    clean_sample_key = manifest_sample_id.split(",")[0].strip()
    
    # 2. Strip operational tracking headers (e.g., VMRC_FRESH_, VMRC_MOD_)
    clean_sample_key = re.sub(r'^VMRC_[A-Z]+_', '', clean_sample_key)
    
    # 3. Strip trailing sequencing extensions if they leaked into the manifest IDs
    clean_sample_key = re.sub(r'\.R[12]\.fq\.gz$|\.se\.fq\.gz$|\.unpaired\.fq\.gz$', '', clean_sample_key)

    # Check for direct key match or sub-string match inside metadata lookup dictionary
    matched_key = None
    if clean_sample_key in metadata_lookup:
        matched_key = clean_sample_key
    else:
        # Loop through metadata to catch cases where metadata strings contain the keys partially
        for meta_key in metadata_lookup.keys():
            if clean_sample_key in meta_key or meta_key in clean_sample_key:
                matched_key = meta_key
                break

    # Bind structural row metrics
    if matched_key:
        subject_source = metadata_lookup[matched_key]["subject_id"]
        timepoint = metadata_lookup[matched_key]["timepoint"]
        matched_meta_data = metadata_lookup[matched_key]["full_meta_row"]
    else:
        subject_source = "UNKNOWN"
        timepoint = "UNKNOWN"
        matched_meta_data = blank_meta_columns

    # Strip line endings first to bypass f-string backslash limits
    clean_row = row.rstrip('\r\n')

    # Construct complete horizontal data row cleanly
    merged_row = f"{clean_row}{manifest_delimiter}{matched_meta_data}\n"

    # Naming convention logic
    combined_name = f"{file_id}_subject.source_subject_id_{subject_source}_sample.timepoint_sequential_{timepoint}"
    combined_name = re.sub(r'[^a-zA-Z0-9_\-.]', '_', combined_name)
    
    sub_dir_path = os.path.join(new_manifest_dir, combined_name)
    os.makedirs(sub_dir_path, exist_ok=True)

    output_filename = f"{combined_name}.txt"
    full_output_path = os.path.join(sub_dir_path, output_filename)

    # Write out the true horizontal layout containing all data fields side-by-side
    with open(full_output_path, "w") as out_f:
        out_f.write(merged_header)
        out_f.write(merged_row)
    
    files_created += 1

print(f"Successfully generated {files_created} horizontally-merged sub-manifests inside '{new_manifest_dir}'.")
