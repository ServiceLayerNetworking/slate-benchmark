#!/bin/bash

latency = 50

# ssh to node1
dst_node="128.110.96.43" # node2
tc qdisc add dev eth0 root handle 1: prio
tc filter add dev eth0 parent 1:0 protocol ip prio 1 u32 match ip dst ${dst_ip} flowid 2:1
tc qdisc add dev eth0 parent 1:1 handle 2: netem delay ${latency}ms

# ssh to node2
dst_node="128.110.96.52" # node1
tc qdisc add dev eth0 root handle 1: prio
tc filter add dev eth0 parent 1:0 protocol ip prio 1 u32 match ip dst ${dst_ip} flowid 2:1
tc qdisc add dev eth0 parent 1:1 handle 2: netem delay ${latency}ms