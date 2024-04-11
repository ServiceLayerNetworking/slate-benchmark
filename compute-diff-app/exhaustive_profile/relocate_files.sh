#!/bin/bash

# Define the target directory
target_directory="./write100kb"

# Check if the target directory exists, if not, create it
if [ ! -d "$target_directory" ]; then
    mkdir -p "$target_directory"
fi

# Find and copy files
find . -type f -name '*-write100kb-west.wrklog' -exec cp {} "$target_directory" \;
find . -type f -name '*-write100kb-west.wrklog' -exec cp {} "$target_directory" \;
