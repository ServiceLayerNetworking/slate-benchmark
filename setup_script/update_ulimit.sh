#!/bin/bash
set -x

echo "NEEDS TO BE EXECUTED FROM NODE0";

for i in $(seq 1 7)
do
    echo $i
    ssh gangmuk@node$i 'echo "sudo ulimit -n 1048576" >> ~/.bashrc'
    # echo "ssh gangmuk@node$i echo "ulimit -n 1048576" >> ~/.bashrc    
done
