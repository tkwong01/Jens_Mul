import os
import re
import sys
import pandas as pd
from collections import defaultdict

working_dir = "/cluster/tufts/hussainlab/tkwong01/Jens_Mul/sub_manifests"
tmp_cov_dir = "/cluster/tufts/hussainlab/tkwong01/Jens_Mul/tmp_mapper_files"
os.makedirs(tmp_cov_dir, exist_ok=True)

mg_pattern = re.compile(
    r"(.+?)\.(?:R1|R2|unpaired)\.fq\.gz_subject\.source_subject_id_(.+?)_sample\.timepoint_sequential_(.+)$"
)

groups = defaultdict(list)

print("="*80)
print("SCANNING SUBDIRECTORIES FOR MAPPER COV OUTPUTS...")
print("="*80)

for root, _, files in os.walk(working_dir):
    for file in files:
        if file.endswith("_mapper.cov"):
            full_path = os.path.join(root, file)
            
            # 1. STRICT CHECK: Isolate Single-End or MT reads completely
            if "MT" in file or ".se.fq.gz" in file:
                group_key = os.path.basename(file).replace("_mapper.cov", "")
                groups[group_key].append(full_path)
                continue 
                
            # 2. Process paired-end MG matching rules
            match = mg_pattern.search(file)
            if match:
                prefix, subject_id, trailing = match.groups()
                group_key = f"{prefix}_{subject_id}_sequential_{trailing}"
                groups[group_key].append(full_path)
            else:
                # Fallback unique key if filename pattern is unexpected
                group_key = os.path.basename(file).replace("_mapper.cov", "")
                groups[group_key].append(full_path)

print(f"Found {len(groups)} unique sample groups.\n")

print("="*80)
print("DETAILED MAPPER COV MERGE LIST")
print("="*80)

for group_key, file_paths in groups.items():
    file_paths = list(set(file_paths))
    
    print(f"\nGroup Destination: {group_key}_mapper.cov")
    print(f"Merging/Copying the following {len(file_paths)} channel files:")
    for path in sorted(file_paths):
        print(f"  └── {os.path.basename(path)}")
    
    merged_df = None
    for path in file_paths:
        df = pd.read_csv(path, sep="\t")
        id_cols = [col for col in df.columns if col.lower() not in ['count', 'coverage', 'reads']]
        count_col = [col for col in df.columns if col.lower() in ['count', 'coverage', 'reads']][0]
        
        if merged_df is None:
            merged_df = df
        else:
            merged_df = pd.merge(merged_df, df, on=id_cols, how="outer", suffixes=('_x', '_y')).fillna(0)
            merged_df[count_col] = merged_df[f"{count_col}_x"] + merged_df[f"{count_col}_y"]
            merged_df = merged_df[id_cols + [count_col]]
            
    if merged_df is not None:
        output_path = os.path.join(tmp_cov_dir, f"{group_key}_mapper.cov")
        merged_df.to_csv(output_path, sep="\t", index=False)

print("\n" + "="*80)
print(f"MERGE COMPLETE: Unified mapper targets written to {tmp_cov_dir}")
print("="*80)

import os
import re
import sys
import pandas as pd
from collections import defaultdict

working_dir = "/cluster/tufts/hussainlab/tkwong01/Jens_Mul/sub_manifests"
tmp_out_dir = "/cluster/tufts/hussainlab/tkwong01/Jens_Mul/tmp_out_files"
os.makedirs(tmp_out_dir, exist_ok=True)

mg_pattern = re.compile(
    r"(.+?)\.(?:R1|R2|unpaired)\.fq\.gz_subject\.source_subject_id_(.+?)_sample\.timepoint_sequential_(.+)$"
)

groups = defaultdict(list)

print("="*80)
print("SCANNING SUBDIRECTORIES FOR MODEL OUTPUTS...")
print("="*80)

for root, _, files in os.walk(working_dir):
    for file in files:
        if file.endswith(".out"):
            full_path = os.path.join(root, file)
            
            # 1. STRICT CHECK: Isolate Single-End or MT reads completely
            if "MT" in file or ".se.fq.gz" in file:
                group_key = os.path.basename(file).replace(".out", "")
                groups[group_key].append(full_path)
                continue 
                
            # 2. Process paired-end MG matching rules
            match = mg_pattern.search(file)
            if match:
                prefix, subject_id, trailing = match.groups()
                group_key = f"{prefix}_{subject_id}_sequential_{trailing}"
                groups[group_key].append(full_path)
            else:
                group_key = os.path.basename(file).replace(".out", "")
                groups[group_key].append(full_path)

print(f"Found {len(groups)} unique sample groups.\n")

print("="*80)
print("DETAILED MERGE LIST")
print("="*80)

for group_key, file_paths in groups.items():
    file_paths = list(set(file_paths))
    
    print(f"\nGroup Destination: {group_key}.out")
    print(f"Merging/Copying the following {len(file_paths)} channel files:")
    for path in sorted(file_paths):
        print(f"  └── {os.path.basename(path)}")
    
    merged_df = None
    for path in file_paths:
        df = pd.read_csv(path, sep="\t")
        if merged_df is None:
            merged_df = df
        else:
            merged_df = pd.merge(merged_df, df, on="Gene", how="outer", suffixes=('_x', '_y')).fillna(0)
            merged_df["Count"] = merged_df["Count_x"] + merged_df["Count_y"]
            merged_df = merged_df[["Gene", "Count"]]
            
    if merged_df is not None:
        merged_df["Count"] = merged_df["Count"].astype(int)
        output_path = os.path.join(tmp_out_dir, f"{group_key}.out")
        merged_df.to_csv(output_path, sep="\t", index=False)

print("\n" + "="*80)
print(f"MERGE COMPLETE: Unified profiles written to {tmp_out_dir}")
print("="*80)
