from kubernetes import client, config
import sys

def get_hotel_deployment_list():
    config.load_kube_config()
    apps_v1_api = client.AppsV1Api()
    cluster_list = ["us-west-1", "us-east-1", "us-south-1", "us-central-1"]
    service_list = ['slateingress', 'frontend', 'recommendation', 'profile', 'rate', 'geo', 'search', 'reservation', 'user', "memcached-profile", "memcached-rate", "memcached-reserve"]
    deploy_list = list()
    for svc in service_list:
        for cluster in cluster_list:
            deploy_list.append(f"{svc}-{cluster}")
    return deploy_list

def set_replicas_for_all_deployments(replica_count):
    config.load_kube_config()
    apps_v1_api = client.AppsV1Api()
    deploy_list = get_hotel_deployment_list()
    # print(f"deploy_list: {deploy_list}")
    deployments = apps_v1_api.list_namespaced_deployment(namespace="default")
    for deployment in deployments.items:
        if deployment.metadata.name in deploy_list:
            deployment.spec.replicas = replica_count
            apps_v1_api.patch_namespaced_deployment(name=deployment.metadata.name, namespace="default", body=deployment)
            print(f"Updating deployment: {deployment.metadata.name}, replicas: {replica_count}")
        else:
            print(f"Skipping deployment: {deployment.metadata.name}")

num_replia = int(sys.argv[1])
if len(sys.argv) != 2:
    print("Usage: python update_app_deploy.py <replica_count>")
    sys.exit(1)
set_replicas_for_all_deployments(num_replia)  # Replace 'X' with the desired number of replicas
