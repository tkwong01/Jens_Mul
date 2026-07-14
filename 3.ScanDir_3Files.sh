#scan for subdirectories that have correct .out _mapper_.cov .mapper.txt and _mutations.txt

cd /cluster/tufts/hussainlab/tkwong01/Jens_Mul/sub_manifests
count=0
for dir in */; do
    ((count++))
    
    missing=""
    
    # Check for any file matching *_mapper.cov
    if ! (ls ${dir}*_mapper.cov >/dev/null 2>&1); then
        missing+=", *_mapper.cov"
    fi
    
    # Check for any file matching *.mapper.txt
    if ! (ls ${dir}*.mapper.txt >/dev/null 2>&1); then
        missing+=", *.mapper.txt"
    fi
    
    # Check for any file matching *_mutations.txt
    if ! (ls ${dir}*_mutations.txt >/dev/null 2>&1); then
        missing+=", *_mutations.txt"
    fi
    
    # If any of the wildcards returned empty, print the directory and its position
    if [ ! -z "$missing" ]; then
        echo "Position $count | Dir: $dir is missing -> ${missing#*, }"
    fi
done
