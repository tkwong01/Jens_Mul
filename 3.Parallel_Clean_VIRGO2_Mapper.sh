#!/bin/bash
#SBATCH --job-name=Parallel_Download_Clean_VIRGO2_1-500
#SBATCH --output=/cluster/tufts/hussainlab/tkwong01/Jens_Mul/Parallel_logs/Parallel_%a.log
#SBATCH --cpus-per-task=4
#SBATCH --mem=128G
#SBATCH --time=04:00:00
#SBATCH --array=1-500%250

#there are 3467 files

cd /cluster/tufts/hussainlab/tkwong01/Jens_Mul

#paths
K2_DB="/cluster/tufts/hussainlab/DATABASES/kraken2_human_db"
VIRGO2_path="/cluster/tufts/hussainlab/DATABASES/VIRGO2"
VIRGO2_fasta="/cluster/tufts/hussainlab/DATABASES/VIRGO2/FastaFiles/VIRGO2.fa"

#CONDA ENVs
module load miniforge
gcp="/cluster/tufts/hussainlab/tkwong01/envs/gcp-tools"
fastp="/cluster/tufts/hussainlab/tkwong01/envs/VIRGO2_env"
virgo2="/cluster/tufts/hussainlab/tkwong01/envs/VIRGO2_env"
module load miniforge kraken2/2.1.3 java/11.0.2 modtree/rocky9 modtree/deprecated
mapper="/cluster/tufts/hussainlab/tkwong01/envs/mapper_env"

# Set threads from SLURM allocation
threads=$SLURM_CPUS_PER_TASK
echo "# threads $threads"

# 1. Get the absolute path of the specific manifest for this array task
MANIFEST_PATH=$(sed -n "${SLURM_ARRAY_TASK_ID}p" 2.manifests_absolute_paths.txt)

# 2. Extract the directory where this manifest lives and its base name
MANIFEST_DIR=$(dirname "$MANIFEST_PATH")
MANIFEST_FILE=$(basename "$MANIFEST_PATH")

# 3. Extract a clean header prefix from the manifest name (e.g., "sample_01.txt" -> "sample_01")
HEADER="${MANIFEST_FILE%.*}"

# 4. CRITICAL: Change directory to where the manifest is stored.
# This ensures ALL downstream tool outputs land exactly in this directory.
cd "$MANIFEST_DIR" || exit 1

# =====================================================================
# Pre-execution Check: Skip if final preserved files already exist
# =====================================================================
if { [ -f "${HEADER}.out" ] || [ -f "${HEADER}.cov" ]; } && [ -f "${HEADER}.mapper.txt" ] && [ -f "${HEADER}_mutations.txt" ]; then
    echo "========================================================"
    echo "Array Task ID: $SLURM_ARRAY_TASK_ID ($HEADER)"
    echo "All final preserved files already exist. Skipping execution."
    echo "========================================================"
    exit 0
fi

echo "========================================================"
echo "Array Task ID: $SLURM_ARRAY_TASK_ID"
echo "Processing Manifest: $MANIFEST_FILE"
echo "Output Directory: $MANIFEST_DIR"
echo "========================================================"

echo "Step 1: Downloading data with portal-client..."
# Pass the local manifest file name since we are already in its directory
source activate "$gcp"
portal-client --manifest "$MANIFEST_FILE" \
              --google-project-id vmrc-462716 \
              --endpoint-priority GS,HTTP

# Dynamically find the downloaded FASTQ file in the current directory
UNP_IN=$(find . -maxdepth 1 -type f -name "*.fastq" -o -name "*.fq" -o -name "*.fastq.gz" -o -name "*.fq.gz" | head -n 1)

if [ -z "$UNP_IN" ]; then
    echo "ERROR: No downloaded fastq file found after portal-client execution."
    exit 1
fi

echo "Step 2: QC and filtering with fastp using input: $UNP_IN..."
conda deactivate
source activate "$virgo2"
fastp -i "$UNP_IN" -o "${HEADER}_cleaned_w.human.fq.gz" \
      -l 50 -W 4 -M 20 --cut_front --cut_tail \
      --thread "$threads" \
      --html "${HEADER}_cleaned_w.human_fastp.html" \
      --json "${HEADER}_cleaned_w.human_fastp.json"


echo "Step 3: Removing human reads with Kraken2..."
kraken2 --db "$K2_DB" \
        --threads "$threads" \
        --quick \
        --gzip-compressed \
        --unclassified-out "${HEADER}_microbial_only.fq" \
        "${HEADER}_cleaned_w.human.fq.gz" > "${HEADER}_kraken_report.txt"

# Compress the clean microbial reads for VIRGO2
gzip -c "${HEADER}_microbial_only.fq" > "${HEADER}_final_for_virgo.fq.gz"


echo "Step 4: Executing VIRGO2 map..."
conda deactivate
source activate "$virgo2"
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
    echo "Error: ${HEADER}.out not found. Something went wrong with VIRGO2. Cutting from .cov"
    awk -F'\t' 'BEGIN {print "Gene\tCount"} {print $1, $4}' OFS='\t' "${HEADER}.cov" > "${HEADER}_from_cov.out"
fi

echo "Task $SLURM_ARRAY_TASK_ID completed successfully. Moving on to mapper"

conda deactivate
source activate "$mapper"
# X-MAPPER: Alignment
echo "Running X-Mapper to extract reference map counts..."

export _JAVA_OPTIONS="-Xmx64g"
x-mapper -Xms512m -Xmx64g \
         --reference "$VIRGO2_fasta" \
         --queries "${HEADER}_final_for_virgo.fq.gz" \
         --num-threads "$threads" \
         --out-vcf "${HEADER}.vcf" \
         --out-sam "${HEADER}.sam" \
         --out-mutations "${HEADER}_mutations.txt" \
         --out-refs-map-count "${HEADER}.mapper.txt" 

# Verify the file was successfully written and is not empty
if [ -s "${HEADER}.mapper.txt" ] && [ -f "${HEADER}.sam" ]; then
    echo "Success: ${HEADER}.mapper.txt and SAM generated successfully. Proceeding with coverage generation."
    samtools sort -O BAM "${HEADER}.sam" > "${HEADER}_temp.bam"
    samtools index "${HEADER}_temp.bam"

    # Extract counts, format with a header, and save as .cov
    echo -e "Gene\tCount" > "${HEADER}_mapper.cov"
    samtools idxstats "${HEADER}_temp.bam" | awk '$3 > 0 {print $1"\t"$3}' >> "${HEADER}_mapper.cov"

    # Clean up the temp BAM files
    rm "${HEADER}_temp.bam" "${HEADER}_temp.bam.bai"
else
    echo "WARNING/ERROR: X-Mapper failed to generate expected outputs. Skipping .cov generation, proceeding directly to cleanup."
fi

# =====================================================================
# Clean-up Phase: Purge heavy intermediate files to conserve cluster storage
# =====================================================================
echo "Initiating intermediate cleanup..."

# 1. Remove the raw downloaded portal-client file
if [ -n "$UNP_IN" ] && [ -f "$UNP_IN" ]; then
    echo "Removing raw downloaded file: $UNP_IN"
    rm -f "$UNP_IN"
fi

# 2. Remove fastp output and logs
rm -f "${HEADER}_cleaned_w.human.fq.gz"
rm -f "${HEADER}_cleaned_w.human_fastp.html" "${HEADER}_cleaned_w.human_fastp.json"

# 3. Remove uncompressed Kraken microbial output and reports
rm -f "${HEADER}_microbial_only.fq"
rm -f "${HEADER}_kraken_report.txt"

# 4. Remove the intermediate compressed microbial FASTQ fed to VIRGO2 and X-Mapper
rm -f "${HEADER}_final_for_virgo.fq.gz"

# 5. Remove X-Mapper heavy intermediate outputs
rm -f "${HEADER}.sam" "${HEADER}.vcf" "${HEADER}.vcf.gz"
echo "========================================================"
#rm -f "${HEADER}_mutations.txt"*
echo "Cleanup complete for $HEADER!"
echo "Preserved: ${HEADER}.out, ${HEADER}.cov, and ${HEADER}.mapper.txt ${HEADER}_mutations.txt (if generated successfully)"
echo "========================================================"
