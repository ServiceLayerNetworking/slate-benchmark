from kubernetes import client, config

def update_deployment_affinity_and_tolerations(deployment_name, namespace, target_node):
    # Load kubeconfig
    config.load_kube_config()

    # Create an instance of the API class
    apps_v1_api = client.AppsV1Api()

    # Fetch the existing deployment
    deployment = apps_v1_api.read_namespaced_deployment(deployment_name, namespace)

    # Prepare node selector requirements based on the target node
    if target_node == "control-plane":
        match_expressions = [client.V1NodeSelectorRequirement(
            key="node-role.kubernetes.io/control-plane",
            operator="Exists"
        )]
    elif target_node == "node5":
        match_expressions = [client.V1NodeSelectorRequirement(
            key="kubernetes.io/hostname",
            operator="In",
            values=["node5.6nodebettercpu.istio-pg0.clemson.cloudlab.us"]
        )]
    else:
        print("Invalid target_node:", target_node)
        return  # Exit the function if the target node is invalid

    # Define node affinity using the prepared match expressions
    node_affinity = client.V1NodeAffinity(
        required_during_scheduling_ignored_during_execution=client.V1NodeSelector(
            node_selector_terms=[client.V1NodeSelectorTerm(
                match_expressions=match_expressions
            )]
        )
    )

    # Update deployment's pod template with node affinity
    if deployment.spec.template.spec.affinity is None:
        deployment.spec.template.spec.affinity = client.V1Affinity()
    deployment.spec.template.spec.affinity.node_affinity = node_affinity

    # Check if tolerations are needed based on the deployment's requirements and node's taints
    # This section is optional and can be customized based on specific needs

    # Update the deployment
    api_response = apps_v1_api.patch_namespaced_deployment(
        name=deployment_name,
        namespace=namespace,
        body=deployment
    )

    print(f"Deployment '{deployment_name}' in namespace '{namespace}' has been updated.")

# Update the 'istio-ingressgateway' deployment in 'istio-system' namespace
update_deployment_affinity_and_tolerations("istio-ingressgateway", "istio-system", "control-plane")
update_deployment_affinity_and_tolerations("istiod", "istio-system", "control-plane")
update_deployment_affinity_and_tolerations("slate-controller", "default", "node5")
