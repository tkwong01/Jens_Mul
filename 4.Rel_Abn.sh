virgo2_env="/cluster/tufts/hussainlab/tkwong01/envs/VIRGO2_env"
VIRGO2_path="/cluster/tufts/hussainlab/DATABASES/VIRGO2"
working_dir="/cluster/tufts/hussainlab/tkwong01/Jens_Mul/sub_manifests"

cd /cluster/tufts/hussainlab/tkwong01/Jens_Mul
OUTPUT_NAME="Jens_Mul_Bacteriocin_Output"

source activate "$virgo2_env"

# 1. Create flat temporary directories for the files
tmp_out_dir="./tmp_out_files"
tmp_cov_dir="./tmp_mapper_files"
mkdir -p "$tmp_out_dir" "$tmp_cov_dir"

# 2. Find and copy the files from subdirectories into the flat folders
# (Using -exec cp {} is much faster and cleaner than reading the text files)
find "$working_dir" -name "*.out" -exec cp {} "$tmp_out_dir/" \;
find "$working_dir" -name "*_mapper.cov" -exec cp {} "$tmp_cov_dir/" \;

# 3. Run VIRGO2 compile pointing directly to the flat directories
python "$VIRGO2_path/VIRGO2.py" compile -i "$tmp_out_dir" -o "$OUTPUT_NAME"_VIRGO2_COMP
python "$VIRGO2_path/VIRGO2.py" compile -i "$tmp_cov_dir" -o "$OUTPUT_NAME"_MAPPER_COMP

# 4. Optional: Clean up the temporary directories afterward to save space
rm -rf "$tmp_out_dir" "$tmp_cov_dir"
