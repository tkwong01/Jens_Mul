#scan for subdirectories that have correct .out _mapper_.cov .mapper.txt and _mutations.txt

cd /cluster/tufts/hussainlab/tkwong01/Jens_Mul/sub_manifests
count=0
csv_file="/cluster/tufts/hussainlab/tkwong01/Jens_Mul/missing_files.csv"

# Create/overwrite the CSV file and add the header line
echo "Position,Directory,Missing_Files" > "$csv_file"

for dir in */; do
    ((count++))
    
    missing=""
    
    # Check for *_mapper.cov
    if ! (ls ${dir}*_mapper.cov >/dev/null 2>&1); then
        missing+="_mapper.cov; "
    fi
    
    # Check for *.mapper.txt
    if ! (ls ${dir}*.mapper.txt >/dev/null 2>&1); then
        missing+=".mapper.txt; "
    fi
    
    # Check for *_mutations.txt
    if ! (ls ${dir}*_mutations.txt >/dev/null 2>&1); then
        missing+="_mutations.txt; "
    fi

    # Check for *_out.txt
    if ! (ls ${dir}*.out >/dev/null 2>&1); then
        missing+=".out; "
    fi
    
    # If anything is missing, report it and log it to the CSV
    if [ ! -z "$missing" ]; then
        # Clean up trailing semicolons/spaces
        missing_clean=$(echo "$missing" | sed 's/; $//')
        
        # 1. Print report to screen
        echo "Position $count | Dir: $dir is missing -> $missing_clean"
        
        # 2. Append cleanly escaped data into the CSV file
        safe_dir=$(echo "$dir" | sed 's/"/""/g')
        echo "$count,\"$safe_dir\",\"$missing_clean\"" >> "$csv_file"
    fi
done

echo "--------------------------------------------------"
echo "Scan complete. CSV saved to: $csv_file"


#find . -type f -name "*.out" -exec wc -l {} + | grep -v ' total$' | sort -n > out_file_lengths.txt
