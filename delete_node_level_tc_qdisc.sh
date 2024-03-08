#!/bin/bash

function delete_tc_qdisc() {
    src_node=$1
    ssh ${src_node} "sudo tc qdisc del dev eno1 root"
}


src_node="gangmuk@apt052.apt.emulab.net" # node1
delete_tc_qdisc ${src_node}
echo "done"

src_node="gangmuk@apt043.apt.emulab.net" # node2
delete_tc_qdisc ${src_node}