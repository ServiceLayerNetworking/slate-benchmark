import subprocess

# Dictionary mapping regions to nodes
region_to_node = {
    "us-west-1": ["node1", "node2", "node3"],
    "us-east-1": ["node4", "node5", "node6"],
    "us-central-1": ["node7", "node8", "node+9"],
    "us-south-1": ["node10", "node11", "node12"]
}

# Function to label nodes using kubectl
def label_nodes():
    for region, nodes in region_to_node.items():
        for node in nodes:
            label = f"topology.kubernetes.io/zone={region}"
            command = f"kubectl label nodes {node}.16node.istio.emulab.net {label}"
            try:
                # Execute the kubectl command
                subprocess.run(command, check=True, shell=True)
                print(f"Successfully labeled {node} with {label}")
            except subprocess.CalledProcessError as e:
                print(f"Failed to label {node}: {e}")

# Run the labeling function
if __name__ == "__main__":
    label_nodes()