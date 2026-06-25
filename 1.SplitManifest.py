import os
import re

metadata_file = "./RealManifests/metadata-6.tsv"
manifest_file = "./RealManifests/manifest-7.tsv"
merged_output_file = "./RealManifests/merged_master_manifest.tsv"
new_manifest_dir = "sub_manifests"

os.makedirs(new_manifest_dir, exist_ok=True)

def normalize_filename(filename):
    """Strips read direction tags and fastq extensions for robust matching."""
    if not filename:
        return ""
    base = re.sub(r'\.R[12]\.fq\.gz$|\.se\.fq\.gz$|\.unpaired\.fq\.gz$|\.fastq\.gz$|\.fq\.gz$', '', filename.strip())
    return base

# ==============================================================================
# STEP 1: MERGE TSVs HORIZONTALLY BY MATCHING file.file_id -> file_id
# ==============================================================================
metadata_lookup = {}

with open(metadata_file, "r") as f:
    meta_lines = f.readlines()

meta_header = meta_lines[0].rstrip("\r\n")
meta_delimiter = "\t" if "\t" in meta_header else ","
meta_header_fields = [field.strip() for field in meta_header.split(meta_delimiter)]

try:
    # Adjusted to match your exact metadata key string
    meta_file_idx = meta_header_fields.index("file.file_id")
except ValueError as e:
    raise ValueError(f"Could not find 'file.file_id' column in metadata: {e}")

# Map every metadata row by its normalized file ID string
for row in meta_lines[1:]:
    if not row.strip():
        continue
    fields = row.rstrip("\r\n").split(meta_delimiter)
    if len(fields) <= meta_file_idx:
        continue
    f_id = fields[meta_file_idx].strip()
    norm_meta_key = normalize_filename(f_id)
    metadata_lookup[norm_meta_key] = meta_delimiter.join(fields)

# Read operational manifest
with open(manifest_file, "r") as f:
    manifest_lines = f.readlines()

manifest_header = manifest_lines[0].rstrip("\r\n")
manifest_delimiter = "\t" if "\t" in manifest_header else ","
manifest_header_fields = [field.strip() for field in manifest_header.split(manifest_delimiter)]

try:
    manifest_file_id_idx = manifest_header_fields.index("file_id")
except ValueError as e:
    raise ValueError(f"Could not find 'file_id' column in manifest: {e}")

master_header = f"{manifest_header}{manifest_delimiter}{meta_header}\n"
blank_meta_columns = manifest_delimiter.join(["None"] * len(meta_header_fields))

master_rows = []
for row in manifest_lines[1:]:
    if not row.strip():
        continue
    fields = row.rstrip("\r\n").split(manifest_delimiter)
    if len(fields) <= manifest_file_id_idx:
        continue
        
    file_id = fields[manifest_file_id_idx].strip()
    norm_manifest_key = normalize_filename(file_id)

    # Match based on normalized base names
    matched_meta_data = metadata_lookup.get(norm_manifest_key, blank_meta_columns)
    
    clean_manifest_row = row.rstrip('\r\n')
    master_rows.append(f"{clean_manifest_row}{manifest_delimiter}{matched_meta_data}\n")

with open(merged_output_file, "w") as out_f:
    out_f.write(master_header)
    out_f.writelines(master_rows)

print(f"--> Step 1 Complete: Saved master horizontal merge to '{merged_output_file}'")

# ==============================================================================
# STEP 2: GENERATE DIRECTORIES AND SUB_MANIFESTS From Merged File
# ==============================================================================
with open(merged_output_file, "r") as f:
    merged_lines = f.readlines()

header = merged_lines[0].rstrip("\r\n")
delimiter = "\t" if "\t" in header else ","
header_fields = [field.strip() for field in header.split(delimiter)]

file_id_idx = header_fields.index("file_id")
subject_idx = header_fields.index("subject.source_subject_id")
timepoint_idx = header_fields.index("sample.timepoint_sequential")

files_created = 0

for row in merged_lines[1:]:
    if not row.strip():
        continue
    fields = row.rstrip("\r\n").split(delimiter)
    
    file_id = fields[file_id_idx].strip()
    subject_source = fields[subject_idx].strip()
    timepoint = fields[timepoint_idx].strip()
    
    if not subject_source or subject_source == "None":
        subject_source = "UNKNOWN"
    if not timepoint or timepoint == "None":
        timepoint = "UNKNOWN"

    combined_name = f"{file_id}_subject.source_subject_id_{subject_source}_sample.timepoint_sequential_{timepoint}"
    combined_name = re.sub(r'[^a-zA-Z0-9_\-.]', '_', combined_name)
    
    sub_dir_path = os.path.join(new_manifest_dir, combined_name)
    os.makedirs(sub_dir_path, exist_ok=True)

    output_filename = f"{combined_name}.txt"
    full_output_path = os.path.join(sub_dir_path, output_filename)

    with open(full_output_path, "w") as out_f:
        out_f.write(merged_lines[0])
        out_f.write(row)
    
    files_created += 1

print(f"--> Step 2 Complete: Generated {files_created} operational manifests inside '{new_manifest_dir}'.")
