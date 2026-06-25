#!/bin/bash
#SBATCH --job-name=Non_Parallel_Download_Clean_VIRGO2
#SBATCH --output=Non_Parallel_logs/Parallel_%a.log
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=02:00:00

# ==============================================================================
# USER CONFIGURATION: Specify what manifest lines to run through
# ==============================================================================
START_LINE=1
END_LINE=5
threads=4  # Set your manually allocated compute threads here
# ==============================================================================

# Paths
K2_DB="/cluster/tufts/hussainlab/DATABASES/kraken2_human_db"
VIRGO2_path="/cluster/tufts/hussainlab/DATABASES/VIRGO2"
VIRGO2_fasta="/cluster/tufts/hussainlab/DATABASES/VIRGO2/FastaFiles/VIRGO2.fa"

# CONDA ENVs
module load miniforge java/11.0.2
gcp="/cluster/tufts/hussainlab/tkwong01/envs/gcp-tools"
virgo2="/cluster/tufts/hussainlab/tkwong01/envs/VIRGO2_env"
mapper="/cluster/tufts/hussainlab/tkwong01/envs/mapper_env"

# Ensure conda activate is accessible inside non-interactive shell execution
source $(conda info --base)/etc/profile.d/conda.sh

echo "Starting sequential processing from line $START_LINE to $END_LINE..."

# Loop through the specified range of lines
for LINE_NUM in $(seq $START_LINE $END_LINE); do

    # Reset working directory back to main for the next iteration path-pull
    cd "$MAIN_DIR" || exit 1

    # 1. Get the absolute path of the specific manifest for this loop iteration
    MANIFEST_PATH=$(sed -n "${LINE_NUM}p" 2.manifests_absolute_paths)
    
    # Safety check if the line requested is empty or out of bounds
    if [ -z "$MANIFEST_PATH" ]; then
        echo "Warning: Line $LINE_NUM is blank or out of bounds. Skipping."
        continue
    fi

    # 2. Extract the directory where this manifest lives and its base name
    MANIFEST_DIR=$(dirname "$MANIFEST_PATH")
    MANIFEST_FILE=$(basename "$MANIFEST_PATH")

    # 3. Extract clean header prefix
    HEADER="${MANIFEST_FILE%.*}"

    # 4. CRITICAL: Change directory to where the manifest is stored
    cd "$MANIFEST_DIR" || exit 1

    echo "========================================================"
    echo "Processing Line Index: $LINE_NUM"
    echo "Processing Manifest: $MANIFEST_FILE"
    echo "Output Directory: $MANIFEST_DIR"
    echo "========================================================"

    echo "Step 1: Downloading data with portal-client..."
    conda activate "$gcp"
    portal-client --manifest "$MANIFEST_FILE" \
                  --google-project-id vmrc-462716 \
                  --endpoint-priority GS,HTTP

    # Dynamically find the downloaded FASTQ file
    UNP_IN=$(find . -maxdepth 1 -type f \( -name "*.fastq" -o -name "*.fq" -o -name "*.fastq.gz" -o -name "*.fq.gz" \) | head -n 1)

    if [ -z "$UNP_IN" ]; then
        echo "ERROR: No downloaded fastq file found after portal-client execution."
        exit 1
    fi

    echo "Step 2: QC and filtering with fastp using input: $UNP_IN..."
    conda activate "$virgo2"
    fastp -i "$UNP_IN" -o "${HEADER}_cleaned_w.human.fq.gz" \
          -l 50 -W 4 -M 20 --cut_front --cut_tail \
          --thread "$threads" \
          --html "${HEADER}_cleaned_w.human_fastp.html" \
          --json "${HEADER}_cleaned_w.human_fastp.json"

    # Clean up massive raw download immediately to preserve storage
    rm "$UNP_IN"

    echo "Step 3: Removing human reads with Kraken2..."
    module load kraken2/2.1.3
    kraken2 --db "$K2_DB" \
            --threads "$threads" \
            --quick \
            --gzip-compressed \
            --unclassified-out "${HEADER}_microbial_only.fq" \
            "${HEADER}_cleaned_w.human.fq.gz" > "${HEADER}_kraken_report.txt"

    # Compress the clean microbial reads and clean up raw intermediate files
    gzip -c "${HEADER}_microbial_only.fq" > "${HEADER}_final_for_virgo.fq.gz"
    rm "${HEADER}_microbial_only.fq"
    rm "${HEADER}_cleaned_w.human.fq.gz"

    echo "Step 4: Executing VIRGO2 map..."
    module unload kraken2/2.1.3
    conda activate "$virgo2"
    
    python "$VIRGO2_path/VIRGO2.py" map \
           -r "${HEADER}_final_for_virgo.fq.gz" \
           -c 1 \
           -p "$threads" \
           -o "$HEADER" \
           -b 0

    echo "Checking for $HEADER.out file..."
    if [ -f "${HEADER}.out" ]; then
        echo "Success: ${HEADER}.out was created!"
    else
        echo "Warning: ${HEADER}.out not found. Generating fallback from .cov file..."
        if [ -f "${HEADER}.cov" ]; then
            awk -F'\t' 'BEGIN {OFS="\t"} {print $1, $4}' "${HEADER}.cov" > "${HEADER}_from_cov.out"
            echo "Fallback complete: ${HEADER}_from_cov.out generated."
        else
            echo "ERROR: Neither .out nor .cov file was found. VIRGO2 mapping failed completely."
            exit 1
        fi
    fi

    echo "Step 5: Running X-Mapper to extract reference map counts..."
    conda activate "$mapper"
    x-mapper --reference "$VIRGO2_fasta" \
             --queries "${HEADER}_final_for_virgo.fq.gz" \
             --num-threads "$threads" \
             --out-refs-map-count "${HEADER}_refs_map_counts.txt"

    if [ -s "${HEADER}_refs_map_counts.txt" ]; then
        echo "Success: ${HEADER}_refs_map_counts.txt generated successfully."
    else
        echo "ERROR: X-Mapper failed to generate mapping counts."
        exit 1
    fi

    echo "Line $LINE_NUM completed successfully."
    echo "--------------------------------------------------------"

done

echo "All specified lines processed successfully!"
