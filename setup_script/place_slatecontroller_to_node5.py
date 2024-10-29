from kubernetes import client, config

def get_node_name_by_partial_hostname(partial_hostname):
    # Load Kubernetes configuration
    config.load_kube_config()
    api_instance = client.CoreV1Api()
    
    # Get all nodes and look for the one containing the partial hostname
    nodes = api_instance.list_node()
    for node in nodes.items:
        hostname = node.metadata.labels.get("kubernetes.io/hostname", "")
        if partial_hostname in hostname:
            return hostname
    
    # If no matching node is found
    print(f"Error: No nodes found with hostname containing '{partial_hostname}'")
    return None

def update_deployment_with_node_affinity(namespace, deployment_name, node_label_key, node_label_value):
    config.load_kube_config()
    api_instance = client.CoreV1Api()
    nodes = api_instance.list_node(label_selector=f"{node_label_key}={node_label_value}")
    if not nodes.items:
        print(f"Error: No nodes found with {node_label_key}={node_label_value}")
        return

    apps_api = client.AppsV1Api()
    deployment = apps_api.read_namespaced_deployment(deployment_name, namespace)
    node_affinity = client.V1NodeAffinity(
        required_during_scheduling_ignored_during_execution=client.V1NodeSelector(
            node_selector_terms=[
                client.V1NodeSelectorTerm(
                    match_expressions=[
                        client.V1NodeSelectorRequirement(
                            key=node_label_key,
                            operator="In",
                            values=[node_label_value]
                        )
                    ]
                )
            ]
        )
    )

    if deployment.spec.template.spec.affinity is None:
        deployment.spec.template.spec.affinity = client.V1Affinity()
    deployment.spec.template.spec.affinity.node_affinity = node_affinity
    apps_api.patch_namespaced_deployment(deployment_name, namespace, deployment)
    print(f"Deployment '{deployment_name}' in namespace '{namespace}' updated to schedule pods on node '{node_label_value}'")

if __name__ == "__main__":
    namespace = 'default'
    deployment_name = 'slate-controller'
    node_label_key = 'kubernetes.io/hostname'
    
    # Get the hostname dynamically based on partial hostname 'node5'
    partial_hostname = 'node5'
    node_label_value = get_node_name_by_partial_hostname(partial_hostname)
    
    if node_label_value:
        update_deployment_with_node_affinity(namespace, deployment_name, node_label_key, node_label_value)


# from kubernetes import client, config

# def update_deployment_with_node_affinity(namespace, deployment_name, node_label_key, node_label_value):
#     config.load_kube_config()
#     api_instance = client.CoreV1Api()
#     nodes = api_instance.list_node(label_selector=f"{node_label_key}={node_label_value}")
#     if not nodes.items:
#         print(f"Error: No nodes found with {node_label_key}={node_label_value}")
#         return

#     apps_api = client.AppsV1Api()
#     deployment = apps_api.read_namespaced_deployment(deployment_name, namespace)
#     node_affinity = client.V1NodeAffinity(
#         required_during_scheduling_ignored_during_execution=client.V1NodeSelector(
#             node_selector_terms=[
#                 client.V1NodeSelectorTerm(
#                     match_expressions=[
#                         client.V1NodeSelectorRequirement(
#                             key=node_label_key,
#                             operator="In",
#                             values=[node_label_value]
#                         )
#                     ]
#                 )
#             ]
#         )
#     )

#     if deployment.spec.template.spec.affinity is None:
#         deployment.spec.template.spec.affinity = client.V1Affinity()
#     deployment.spec.template.spec.affinity.node_affinity = node_affinity
#     apps_api.patch_namespaced_deployment(deployment_name, namespace, deployment)
#     print(f"Deployment '{deployment_name}' in namespace '{namespace}' updated to schedule pods on node '{node_label_value}'")

# if __name__ == "__main__":
#     namespace = 'default'
#     deployment_name = 'slate-controller'
#     node_label_key = 'kubernetes.io/hostname'
#     node_label_value = 'node2.slate1.istio-pg0.clemson.cloudlab.us'
#     update_deployment_with_node_affinity(namespace, deployment_name, node_label_key, node_label_value)
