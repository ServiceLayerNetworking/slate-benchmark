#!/bin/bash
set -x

echo "NEEDS TO BE EXECUTED FROM NODE0";
sudo sed -i "2c * hard nofile 922337203685477" /etc/security/limits.conf
for i in $(seq 1 7)
do
    echo "Processing node$i"
    ssh gangmuk@node$i 'sudo sed -i "2c * hard nofile 922337203685477" /etc/security/limits.conf'
done
