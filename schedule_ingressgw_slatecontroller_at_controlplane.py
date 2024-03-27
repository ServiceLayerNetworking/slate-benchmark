from kubernetes import client, config

def update_deployment_affinity_and_tolerations(deployment_name, namespace):
    # Load kubeconfig
    config.load_kube_config()

    # Create an instance of the API class
    apps_v1_api = client.AppsV1Api()

    # Fetch the existing deployment
    deployment = apps_v1_api.read_namespaced_deployment(deployment_name, namespace)

    # Define node affinity
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

    # Define tolerations
    tolerations = [
        client.V1Toleration(
            key="node-role.kubernetes.io/control-plane",
            operator="Exists",
            effect="NoSchedule"
        )
    ]

    # Update deployment's pod template with affinity and tolerations
    if deployment.spec.template.spec.affinity is None:
        deployment.spec.template.spec.affinity = client.V1Affinity()
    deployment.spec.template.spec.affinity.node_affinity = node_affinity

    deployment.spec.template.spec.tolerations = tolerations

    # Update the deployment
    api_response = apps_v1_api.patch_namespaced_deployment(
        name=deployment_name,
        namespace=namespace,
        body=deployment
    )

    print(f"Deployment '{deployment_name}' in namespace '{namespace}' has been updated.")

# Update the 'istio-ingressgateway' deployment in 'istio-system' namespace
update_deployment_affinity_and_tolerations("istio-ingressgateway", "istio-system")
update_deployment_affinity_and_tolerations("istiod", "istio-system")
update_deployment_affinity_and_tolerations("slate-controller", "default")
