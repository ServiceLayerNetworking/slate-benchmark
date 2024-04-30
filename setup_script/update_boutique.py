from kubernetes import client, config

def update_deployment_image(deployment_name, new_image):
    # Configure API key authorization: Configuration
    config.load_kube_config()  # Make sure your .kube/config is set up correctly

    # Create an API instance
    api_instance = client.AppsV1Api()

    # Get the specified deployment in the default namespace
    deployment = api_instance.read_namespaced_deployment(deployment_name, 'default')
    
    # Update the container image
    deployment.spec.template.spec.containers[0].image = new_image
    
    # Update the deployment
    api_instance.patch_namespaced_deployment(name=deployment_name, namespace='default', body=deployment)
    print(f"Updated {deployment_name} to use image {new_image}")

def main():
    # Load configuration from default location
    config.load_kube_config()

    # Create an API instance
    api_instance = client.AppsV1Api()

    # List all deployments in the default namespace
    api_response = api_instance.list_namespaced_deployment(namespace='default')
    
    for deployment in api_response.items:
        deployment_name = deployment.metadata.name
        
        if deployment_name.startswith("frontend"):
            update_deployment_image(deployment_name, "docker.io/adiprerepa/boutique-frontend")
        elif deployment_name.startswith("checkoutservice"):
            update_deployment_image(deployment_name, "docker.io/adiprerepa/boutique-checkout")
        elif deployment_name.startswith("recommendationservice"):
            update_deployment_image(deployment_name, "docker.io/adiprerepa/boutique-recommendation")

if __name__ == "__main__":
    main()