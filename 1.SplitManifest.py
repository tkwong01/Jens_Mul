import os

manifest = "/Users/tkwong01/Desktop/MTMG_Stata_Plots/MT_MGPaired/manifest_used/SameDay.tsv"
new_manifest_dir = "sub_manifests"

# Ensure the main base directory exists
os.makedirs(new_manifest_dir, exist_ok=True)

with open(manifest, "r") as f:
    lines = f.readlines()

header = lines[0]
data_rows = lines[1:]

# Detect delimiter (Tab or Comma)
delimiter = "\t" if "\t" in header else ","

# Clean up header fields to find "file.name"
header_fields = [field.strip() for field in header.split(delimiter)]

try:
    filename_idx = header_fields.index("file.name")
except ValueError:
    raise ValueError("Could not find a column named 'file.name' in the header.")

files_created = 0

for row in data_rows:
    if not row.strip():
        continue
    
    # Split the row to extract the specific column value
    row_fields = row.split(delimiter)
    
    # Grab the filename and strip any accidental whitespace
    base_filename = row_fields[filename_idx].strip()
    
    # Ensure file ends with .txt
    if not base_filename.lower().endswith(".txt"):
        output_filename = f"{base_filename}.txt"
    else:
        output_filename = base_filename

    # Get a clean folder name by removing '.txt' or '.tsv' if present
    # This prevents creating a folder named "image.txt" 
    folder_name = base_filename.rsplit('.', 1)[0] if '.' in base_filename else base_filename
    
    # Create the specific subdirectory path (e.g., sub_manifests/image_001)
    sub_dir_path = os.path.join(new_manifest_dir, folder_name)
    os.makedirs(sub_dir_path, exist_ok=True)

    # Set the final file path (e.g., sub_manifests/image_001/image_001.txt)
    full_output_path = os.path.join(sub_dir_path, output_filename)

    # Write the header and the specific row to the new file
    with open(full_output_path, "w") as out_f:
        out_f.write(header)
        out_f.write(row)
    
    files_created += 1

print(f"Successfully created {files_created} individual directories and manifest files inside '{new_manifest_dir}'.")
