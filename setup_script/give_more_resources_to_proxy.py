import subprocess
import yaml

def get_deployments(namespace):
    cmd = f"kubectl get deployments -n {namespace} -o yaml"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(f"Failed to fetch deployments in namespace {namespace}: " + result.stderr)
    return yaml.safe_load(result.stdout)

def update_annotations(deployments, annotations):
    for item in deployments['items']:
        item['spec']['template']['metadata'].setdefault('annotations', {}).update(annotations)
    updated_yaml = yaml.dump(deployments)
    
    # Apply updated deployments without writing to file
    result = subprocess.run("kubectl apply -f -", shell=True, input=updated_yaml, text=True, capture_output=True)
    if result.returncode != 0:
        raise Exception("Failed to apply updated deployments: " + result.stderr)
    print("Updated deployments applied successfully")

# Annotations to be added to each deployment
annotations = {
    'sidecar.istio.io/proxyCPU': '100m',
    'sidecar.istio.io/proxyMemory': '128Mi',
    'sidecar.istio.io/proxyCPULimit': '5000m',
    'sidecar.istio.io/proxyMemoryLimit': '1Gi'
}

# Main script execution
namespace = 'default'  # Specify the namespace here
try:
    deployments = get_deployments(namespace)
    update_annotations(deployments, annotations)
except Exception as e:
    print(str(e))


# import subprocess
# import yaml

# def get_deployments(namespace):
#     cmd = f"kubectl get deployments -n {namespace} -o yaml"
#     result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
#     if result.returncode != 0:
#         raise Exception("Failed to fetch deployments: " + result.stderr)
#     return yaml.safe_load(result.stdout)

# # def filter_deployments(deployments):
# #     service_list = ['slateingress', 'frontend', 'recommendation', 'profile', 'rate', 'geo', 'search', 'reservation', 'user']
# #     selected_deployments = list()
# #     for deploy in deployments:
# #         if deploy.metadata.name in service_list:
# #             selected_deployments.append(deploy)
# #     return selected_deployments
    

# def update_annotations(deployments, annotations):
#     for item in deployments['items']:
#         item['spec']['template']['metadata'].setdefault('annotations', {}).update(annotations)
#     updated_yaml = yaml.dump(deployments)
#     with open("updated_deployments.yaml", "w") as file:
#         file.write(updated_yaml)
#     cmd = "kubectl apply -f updated_deployments.yaml"
#     result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
#     if result.returncode != 0:
#         raise Exception("Failed to apply updated deployments: " + result.stderr)
#     print("Updated deployments applied successfully")

# # Annotations to be added to each deployment
# annotations = {
#     'sidecar.istio.io/proxyCPU': '100m',
#     'sidecar.istio.io/proxyMemory': '128Mi',
#     'sidecar.istio.io/proxyCPULimit': '5000m',
#     'sidecar.istio.io/proxyMemoryLimit': '1Gi'
# }

# # Main script execution
# namespace = 'default'  # Specify the namespace here
# try:
#     deployments = get_deployments(namespace)
#     update_annotations(deployments, annotations)
# except Exception as e:
#     print(str(e))
