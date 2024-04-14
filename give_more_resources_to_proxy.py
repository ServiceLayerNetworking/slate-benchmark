import subprocess
import yaml

def get_deployments(namespace):
    # Get all deployments in the specified namespace
    cmd = f"kubectl get deployments -n {namespace} -o yaml"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception("Failed to fetch deployments: " + result.stderr)
    return yaml.safe_load(result.stdout)

def update_annotations(deployments, annotations):
    # Modify the deployments with the new annotations
    for item in deployments['items']:
        item['spec']['template']['metadata'].setdefault('annotations', {}).update(annotations)

    # Dump updated deployments to a temporary YAML file
    updated_yaml = yaml.dump(deployments)
    with open("updated_deployments.yaml", "w") as file:
        file.write(updated_yaml)

    # Apply the updated YAML using kubectl
    cmd = "kubectl apply -f updated_deployments.yaml"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception("Failed to apply updated deployments: " + result.stderr)
    print("Updated deployments applied successfully")

# Annotations to be added to each deployment
annotations = {
    'sidecar.istio.io/proxyCPU': '100m',
    'sidecar.istio.io/proxyCPULimit': '4000m',
    'sidecar.istio.io/proxyMemory': '128Mi',
    'sidecar.istio.io/proxyMemoryLimit': '1Gi'
}

# Main script execution
namespace = 'default'  # Specify the namespace here
try:
    deployments = get_deployments(namespace)
    update_annotations(deployments, annotations)
except Exception as e:
    print(str(e))
