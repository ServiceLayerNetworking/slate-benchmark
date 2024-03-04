#!/bin/bash

# Get all nodes and their labels
nodes_with_labels=$(kubectl get nodes --show-labels)
node1=$(echo "$nodes_with_labels" | grep 'node1' | awk '{print $1}')
node2=$(echo "$nodes_with_labels" | grep 'node2' | awk '{print $1}')
kubectl label node $node2 topology.kubernetes.io/zone=us-west-1 --overwrite
kubectl label node $node1 topology.kubernetes.io/zone=us-east-1 --overwrite
echo "kubectl label node $node1 topology.kubernetes.io/zone=us-west-1 --overwrite"
echo "kubectl label node $node2 topology.kubernetes.io/zone=us-east-1 --overwrite"
exit

## Filter out master nodes and extract just the node names
## Replace 'node-role.kubernetes.io/master' with the appropriate label for master nodes in your cluster
#worker_node_names=$(echo "$nodes_with_labels" | grep -v 'node-role.kubernetes.io/master' | awk '{if (NR!=1) print $1}')
#worker_nodes=($worker_node_names)
#for node in "${worker_nodes[@]}"; do
#    echo "$node"
#    if [[ "$node" == *"node1"* ]]; then
#        kubectl label node $node topology.kubernetes.io/zone=us-west-1 --overwrite
#        echo "kubectl label node $node topology.kubernetes.io/zone=us-west-1 --overwrite"
#    fi
#    if [[ "$node" == *"node2"* ]]; then
#        kubectl label node $node topology.kubernetes.io/zone=us-east-1 --overwrite
#        echo "kubectl label node $node topology.kubernetes.io/zone=us-east-1 --overwrite"
#    fi
#done
