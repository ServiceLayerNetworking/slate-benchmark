from kubernetes import client, config

def schedule_to_control_plane(deployment_name, namespace):
     config.load_kube_config()
     apps_v1_api = client.AppsV1Api()
     deployment = apps_v1_api.read_namespaced_deployment(deployment_name, namespace)
     node_affinity = client.V1NodeAffinity(
         required_during_scheduling_ignored_during_execution=client.V1NodeSelector(
             node_selector_terms=[client.V1NodeSelectorTerm(
                 match_expressions=[client.V1NodeSelectorRequirement(
                     key="node-role.kubernetes.io/control-plane",
                     operator="Exists"
                 )]
             )]
         )
     )
     tolerations = [
         client.V1Toleration(
             key="node-role.kubernetes.io/control-plane",
             operator="Exists",
             effect="NoSchedule"
         )
     ]
     if deployment.spec.template.spec.affinity is None:
         deployment.spec.template.spec.affinity = client.V1Affinity()
     deployment.spec.template.spec.affinity.node_affinity = node_affinity
     deployment.spec.template.spec.tolerations = tolerations
     api_response = apps_v1_api.patch_namespaced_deployment(
         name=deployment_name,
         namespace=namespace,
         body=deployment
     )
     print(f"Deployment '{deployment_name}' in namespace '{namespace}' has been updated.")


def update_hpa(namespace, hpa_name, min_replicas, max_replicas):
    config.load_kube_config()
    api_instance = client.AutoscalingV1Api()
    if max_replicas < min_replicas:
        print("Error: maxReplicas must be greater than or equal to minReplicas")
        return
    body = {
        "spec": {
            "minReplicas": min_replicas,
            "maxReplicas": max_replicas
        }
    }
    try:
        api_instance.patch_namespaced_horizontal_pod_autoscaler(hpa_name, namespace, body)
        print("HPA updated successfully.")
    except client.exceptions.ApiException as e:
        print("Failed to update HPA:", e)
    print(f"Update HPA '{hpa_name}, maxReplicas={max_replicas}, minReplicas={min_replicas}")
    
    
def remove_resource_limits(namespace, deployment_name):
    config.load_kube_config()
    apps_v1 = client.AppsV1Api()
    patch = {
        "spec": {
            "template": {
                "spec": {
                    "containers": [
                        {
                            "name": "istio-proxy",  # You might need to adjust this if the container name differs
                            "resources": {
                                "limits": None
                            }
                        }
                    ]
                }
            }
        }
    }
    try:
        apps_v1.patch_namespaced_deployment(name=deployment_name, namespace=namespace, body=patch)
        print(f"Resource limits removed from deployment {deployment_name} in namespace {namespace}.")
    except client.exceptions.ApiException as e:
        print("Failed to patch the deployment:", e)
        
if __name__ == "__main__":
    namespace = 'istio-system'  # Change this to the namespace of your HPA
    hpa_name = 'istio-ingressgateway'
    min_replicas = 5
    max_replicas = 10
    update_hpa(namespace, hpa_name, min_replicas, max_replicas)
    # schedule_to_control_plane("istio-ingressgateway", "istio-system")
    # schedule_to_control_plane("istiod", "istio-system")
    remove_resource_limits("istio-system", "istio-ingressgateway")

