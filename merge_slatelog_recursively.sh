output_filename=$1
find . -type f -name "*.slatelog" -exec cat {} + > ${output_filename}