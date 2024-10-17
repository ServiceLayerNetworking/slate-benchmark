import sys
from kubernetes import client, config

def scale_deployments_old(namespace, replica_count, exclude_deployments=[]):
    # Load kubeconfig (assumes you have access to the cluster)
    config.load_kube_config()

    # Create an instance of the API class
    apps_v1 = client.AppsV1Api()

    # Get all deployments in the specified namespace
    deployments = apps_v1.list_namespaced_deployment(namespace)

    for deployment in deployments.items:
        # Skip deployments in the exclude list
        if deployment.metadata.name in exclude_deployments:
            continue
        
        # Define the new number of replicas
        body = {
            "spec": {
                "replicas": str(replica_count)
            }
        }

        # Scale the deployment
        response = apps_v1.patch_namespaced_deployment_scale(
            name=deployment.metadata.name,
            namespace=namespace,
            body=body
        )

        print(f"Scaled deployment {deployment.metadata.name} to {replica_count} replicas")


def scale_deployments(namespace, replica_count, exclude_deployments=[]):
    # Load kubeconfig (assumes you have access to the cluster)
    config.load_kube_config()

    # Create an instance of the API class
    apps_v1 = client.AppsV1Api()

    # Get all deployments in the specified namespace
    deployments = apps_v1.list_namespaced_deployment(namespace)

    for deployment in deployments.items:
        # Skip deployments in the exclude list
        if deployment.metadata.name in exclude_deployments:
            continue
        
        # Define the new number of replicas
        body = {
            "spec": {
                "replicas": 4
            }
        }

        # Scale the deployment
        response = apps_v1.patch_namespaced_deployment_scale(
            name=deployment.metadata.name,
            namespace=namespace,
            body=body
        )

        print(f"Scaled deployment {deployment.metadata.name} to {replica_count} replicas")

if len(sys.argv) != 2:
    print("include replica count")
else:
    count = int(sys.argv[1])
    scale_deployments("default", count, exclude_deployments=["slate-controller"])