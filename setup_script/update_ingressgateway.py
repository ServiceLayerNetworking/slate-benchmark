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


def update_hpa(namespace, hpa_name, min_replicas):
    config.load_kube_config()
    api_instance = client.AutoscalingV1Api()
    hpa = api_instance.read_namespaced_horizontal_pod_autoscaler(hpa_name, namespace)
    hpa.spec.min_replicas = min_replicas
    api_instance.patch_namespaced_horizontal_pod_autoscaler(hpa_name, namespace, hpa)
    print(f"HPA '{hpa_name}' in namespace '{namespace}' has been updated to minReplicas={min_replicas}")

if __name__ == "__main__":
    namespace = 'istio-system'  # Change this to the namespace of your HPA
    hpa_name = 'istio-ingressgateway'
    min_replicas = 3
    update_hpa(namespace, hpa_name, min_replicas)
    schedule_to_control_plane("istio-ingressgateway", "istio-system")
    schedule_to_control_plane("istiod", "istio-system")


## It is deprecated. because there is hpa for istio-ingressgateway that has 1 minReplicas
# def update_replicas(deployment_name, namespace, replicas):
#     config.load_kube_config()
#     api_instance = client.AppsV1Api()
#     patch = {
#         "spec": {
#             "replicas": replicas
#         }
#     }
#     try:
#         api_response = api_instance.patch_namespaced_deployment(
#             name=deployment_name,
#             namespace=namespace,
#             body=patch
#         )
#         print(f"Update num of replicas: {deployment_name}, num: {replicas}")
#     except client.rest.ApiException as e:
#         print("An error occurred: %s" % e)
# update_replicas("istio-ingressgateway", "istio-system", 4)
