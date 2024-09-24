from kubernetes import client, config
import sys

def set_replicas_for_all_deployments(replica_count):
    config.load_kube_config()
    apps_v1_api = client.AppsV1Api()
    # deploy_list = get_hotel_deployment_list()
    # print(f"deploy_list: {deploy_list}")
    deployments = apps_v1_api.list_namespaced_deployment(namespace="default")
    for deployment in deployments.items:
        
        ## in case sslateingress is bottleneck.
        # if "sslateingress" in deployment.metadata.name:
        #     deployment.spec.replicas = replica_count
        #     apps_v1_api.patch_namespaced_deployment(name=deployment.metadata.name, namespace="default", body=deployment)
        #     print(f"Updating deployment: {deployment.metadata.name}, replicas: {replica_count}")
        # else:
        #     print(f"Skipping deployment: {deployment.metadata.name}")
            
        if "slate-controller" == deployment.metadata.name:
            continue
        
        deployment.spec.replicas = replica_count
        apps_v1_api.patch_namespaced_deployment(name=deployment.metadata.name, namespace="default", body=deployment)
        print(f"Updating deployment: {deployment.metadata.name}, replicas: {replica_count}")

if len(sys.argv) != 2:
    print("Usage: python update_app_deploy.py <replica_count>")
    sys.exit(1)
num_replia = int(sys.argv[1])
set_replicas_for_all_deployments(num_replia)  # Replace 'X' with the desired number of replicas
