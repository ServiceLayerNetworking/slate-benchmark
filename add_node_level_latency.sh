#!/bin/bash

function add_latency() {
    src_node=$1
    src_node_ip=$2
    dst_node=$3
    dst_node_ip=$4
    latency=$5
    ssh ${src_node} "sudo tc qdisc del dev eno1 root"
    echo 0
    ssh ${src_node} "sudo tc qdisc add dev eno1 root handle 1: prio"
    echo 1
    ssh ${src_node} "sudo tc filter add dev eno1 parent 1:0 protocol ip prio 1 u32 match ip dst ${dst_node_ip} flowid 2:1"
    echo 2 ${dst_node} ${dst_node_ip}
    ssh ${src_node} "sudo tc qdisc add dev eno1 parent 1:1 handle 2: netem delay ${latency}ms"
    echo 3

}

node1_name=$1
node1_ip=$2
node2_name=$3
node2_ip=$4
latency=$5

#node1_ip="128.110.96.52"
#node2_ip="128.110.96.43"
#node1_name="apt052.apt.emulab.net" # node1
#node2_name="apt043.apt.emulab.net" # node2
#latency=20

add_latency ${node1_name} ${node1_ip} ${node2_name} ${node2_ip} ${latency}
add_latency ${node2_name} ${node2_ip} ${node1_name} ${node1_ip} ${latency}
