from kubernetes import client, config

def update_deployment_affinity_and_tolerations(deployment_name, namespace, target_node):
    config.load_kube_config()
    apps_v1_api = client.AppsV1Api()
    deployment = apps_v1_api.read_namespaced_deployment(deployment_name, namespace)
    match_expressions = [client.V1NodeSelectorRequirement(
        key="kubernetes.io/hostname",
        operator="In",
        values=["node5.6nodebettercpu.istio-pg0.clemson.cloudlab.us"]
    )]
    node_affinity = client.V1NodeAffinity(
        required_during_scheduling_ignored_during_execution=client.V1NodeSelector(
            node_selector_terms=[client.V1NodeSelectorTerm(
                match_expressions=match_expressions
            )]
        )
    )
    if deployment.spec.template.spec.affinity is None:
        deployment.spec.template.spec.affinity = client.V1Affinity()
    deployment.spec.template.spec.affinity.node_affinity = node_affinity
    api_response = apps_v1_api.patch_namespaced_deployment(
        name=deployment_name,
        namespace=namespace,
        body=deployment
    )
    print(f"Deployment '{deployment_name}' in namespace '{namespace}' has been updated.")

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

# Update the 'istio-ingressgateway' deployment in 'istio-system' namespace
schedule_to_control_plane("istio-ingressgateway", "istio-system")
schedule_to_control_plane("istiod", "istio-system")
schedule_to_control_plane("slate-controller", "default")
# schedule_to_a_certain_node("slate-controller", "default", "node5")
