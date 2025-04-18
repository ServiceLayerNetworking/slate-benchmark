import sys
from kubernetes import client, config

def scale_igw(namespace, replica_count, deployments=[]):
    # Load kubeconfig (assumes you have access to the cluster)
    config.load_kube_config()

    # Create an instance of the API class
    apps_v1 = client.AppsV1Api()

    # Get all deployments in the specified namespace
    deployments = apps_v1.list_namespaced_deployment(namespace)

    for deployment in deployments.items:
        # Skip deployments in the exclude list
        if deployment.metadata.name not in deployments:
            continue
        
        # Define the new number of replicas
        body = {
            "spec": {
                "replicas": replica_count
            }
        }

        # Scale the deployment
        response = apps_v1.patch_namespaced_deployment_scale(
            name=deployment.metadata.name,
            namespace=namespace,
            body=body
        )

        print(f"Scaled deployment {deployment.metadata.name} to {replica_count} replicas")

scale_igw("istio-system", 4, deployments=["istio-ingressgateway"])