from kubernetes import client, config

def update_deployment_rollout_settings(namespace='default'):
    config.load_kube_config()
    apps_v1 = client.AppsV1Api()
    deployments = apps_v1.list_namespaced_deployment(namespace)
    for deployment in deployments.items:
        deployment.spec.strategy = client.V1DeploymentStrategy(
            rolling_update=client.V1RollingUpdateDeployment(
                max_surge='100%',
                max_unavailable='0%'
            ),
            type='RollingUpdate'
        )
        try:
            api_response = apps_v1.replace_namespaced_deployment(
                name=deployment.metadata.name,
                namespace=namespace,
                body=deployment
            )
            print(f"Deployment {deployment.metadata.name} updated successfully.")
        except Exception as e:
            print(f"Failed to update deployment {deployment.metadata.name}: {e}")

if __name__ == "__main__":
    update_deployment_rollout_settings(namespace='default')  # You can specify a different namespace if needed
