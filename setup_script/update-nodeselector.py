import sys
from kubernetes import client, config

def update_deployment_node_selector(deployment_name, namespace, node_name):
    # Load the Kubernetes config from default location
    config.load_kube_config()

    # Create an API client
    apps_v1 = client.AppsV1Api()

    try:
        # Get the deployment object
        deployment = apps_v1.read_namespaced_deployment(deployment_name, namespace)
        
        # Modify the nodeSelector field
        if not deployment.spec.template.spec.node_selector:
            deployment.spec.template.spec.node_selector = {}
        deployment.spec.template.spec.node_selector['kubernetes.io/hostname'] = node_name
        
        # Update the deployment with the new nodeSelector
        apps_v1.patch_namespaced_deployment(deployment_name, namespace, deployment)
        print(f"Updated deployment '{deployment_name}' in namespace '{namespace}' to use node '{node_name}'.")
    except client.exceptions.ApiException as e:
        print(f"Exception occurred: {e}")

if len(sys.argv) != 4:
    print("usage: python update-nodeselector.py <deploy> <ns> <node hostname>")
else:
    deploy = sys.argv[1]
    ns = sys.argv[2]
    hostname = sys.argv[3]
    update_deployment_node_selector(deploy, ns, hostname)
