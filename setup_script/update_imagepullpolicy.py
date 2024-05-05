from kubernetes import client, config

def update_image_pull_policy(namespace='default', new_pull_policy='IfNotPresent', exclude=["slate-controller"]):
    config.load_kube_config()
    apps_v1 = client.AppsV1Api()
    deployments = apps_v1.list_namespaced_deployment(namespace)
    for deployment in deployments.items:
        if deployment.metadata.name in exclude:
            continue
        for container in deployment.spec.template.spec.containers:
            container.image_pull_policy = new_pull_policy
        try:
            api_response = apps_v1.replace_namespaced_deployment(
                name=deployment.metadata.name,
                namespace=namespace,
                body=deployment
            )
            print(f"Deployment {deployment.metadata.name} updated successfully. ImagePullPolicy set to {new_pull_policy}.")
        except Exception as e:
            print(f"Failed to update deployment {deployment.metadata.name}: {e}")

if __name__ == "__main__":
    update_image_pull_policy(new_pull_policy='Always', exclude=["slate-controller"])  # You can specify a different namespace if needed
