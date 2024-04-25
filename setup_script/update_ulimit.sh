#!/bin/bash
set -x

echo "NEEDS TO BE EXECUTED FROM NODE0";

for i in {1..15}
do
    ssh gangmuk@node$i echo "ulimit -n 1048576" >> ~/.bashrc
    echo "ssh gangmuk@node$i echo "ulimit -n 1048576" >> ~/.bashrc    
done