import os
import subprocess
from datetime import datetime
from kubernetes import client, config
import math
import time
import concurrent.futures
import sys
import os
import concurrent.futures
from datetime import datetime
import copy
import xml.etree.ElementTree as ET
from pprint import pprint
import atexit
import signal

CLOUDLAB_CONFIG_XML="/users/gangmuk/projects/slate-benchmark/config.xml"

def are_all_pods_ready(namespace='default'):
    config.load_kube_config()
    v1 = client.CoreV1Api()
    pods = v1.list_namespaced_pod(namespace)
    all_pods_ready = True
    for pod in pods.items:
        # Check if the pod is in the process of terminating
        if pod.metadata.deletion_timestamp is not None:
            all_pods_ready = False
            break  # Pod is terminating, so not all pods are ready
        # Check for pods that are not in the 'Running' phase
        if pod.status.phase != 'Running':
            all_pods_ready = False
            break
        if pod.status.conditions is None:
            all_pods_ready = False
            break
        ready_condition_found = False
        for condition in pod.status.conditions:
            if condition.type == 'Ready':
                ready_condition_found = True
                if condition.status != 'True':
                    all_pods_ready = False
                    break  # Break out of the inner loop
        if not ready_condition_found:
            # If no Ready condition is found, consider the pod not ready
            all_pods_ready = False
            break
    return all_pods_ready

def kubectl_cp_from_host_to_slate_controller_pod(src_in_host, dst_in_pod):
    success, slate_controller_pod = run_command("kubectl get pods -l app=slate-controller -o custom-columns=:metadata.name")
    # print(f"Try kubectl_cp_from_host_to_slate_controller_pod")
    print(f"- src_in_host: {src_in_host}")
    print(f"- dst_in_pod: {slate_controller_pod}:{dst_in_pod}")
    run_command(f"kubectl cp {src_in_host} {slate_controller_pod}:{dst_in_pod}")
    print(f"finish scp from {src_in_host} to {slate_controller_pod}:{dst_in_pod}")


def get_pod_name_from_deploy(deployment_name, namespace='default'):
    config.load_kube_config()
    api_instance = client.AppsV1Api()
    try:
        success, pod_name = run_command(f"kubectl get pods -l app={deployment_name} -o custom-columns=:metadata.name")
        return pod_name
    except client.ApiException as e:
        print(f"Error fetching the pod name for deployment {deployment_name}: {e}")
        assert False
        
        
def kubectl_cp_from_slate_controller_to_host(src_in_pod, dst_in_host):
    slate_controller_pod = get_pod_name_from_deploy("slate-controller")
    print(f"- src_in_pod: {slate_controller_pod}:{src_in_pod}")
    print(f"- dst_in_host: {dst_in_host}")
    # if check_file_exists_in_pod(slate_controller_pod, "default", src_in_pod) == False:
    #     print(f"Skip scp. {src_in_pod} does not exist in the slate-controller pod")
    #     return
    # slate_controller_pod = run_command("kubectl get pods -l app=slate-controller -o custom-columns=:metadata.name")
    temp_file = "temp_file.txt"
    success, ret = run_command(f"kubectl cp {slate_controller_pod}:{src_in_pod} {temp_file}", required=False)
    if ret != False:
        # success
        run_command(f"mv {temp_file} {dst_in_host}", required=True)
        return True
    else:
        # fail
        print(f"\tSkip scp. {src_in_pod} does not exist in the slate-controller pod")
        return False
    
def run_command(command, required=True, print_error=True, nonblock=False):
    """Run shell command and return its output"""
    try:
        ''' Popen is asynchronous and non-blocking, while check_output is synchronous and blocking.'''
        if nonblock:
            process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            stdout, stderr = process.communicate()  # If you decide to wait and capture output for debugging
            print("STDOUT:", stdout)
            print("STDERR:", stderr)
            return True, "NotOutput-this-is-nonblocking-execution"
        else:
            output = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT)
            return True, output.decode('utf-8').strip()
    except subprocess.CalledProcessError as e:
        if print_error:
            print(f"ERROR command: {command}")
            print(f"ERROR output: {e.output.decode('utf-8').strip()}")
        if required:
            print("Exit...")
            assert False
        else:
            return False, e.output.decode('utf-8').strip()
        
def update_env_txt(CONFIG):
    local_env_file = "local_env.txt"
    with open(local_env_file, "w") as file:
        for key, value in CONFIG.items():
            file.write(f"{key},{value}\n") 
    print(f"write {local_env_file}")
    return local_env_file

def record_pod_resource_allocation(wrk_log_path, target_cluster_rps):
    if target_cluster_rps == 0:
        return
    with open(wrk_log_path, "a") as f:
        f.write("\n-- start of resource allocation --\n")
        resource_allocation = get_pod_resource_allocation()
        f.write(resource_allocation)
        f.write("-- end of resource allocation --\n")

def get_pod_resource_usage(namespace='default'):
    config.load_kube_config()
    api_instance = client.CoreV1Api()
    custom_api = client.CustomObjectsApi()
    namespaces = ["default", "istio-system"]
    resource_allocation = "Namespace,Pod Name,Container Name,CPU Usage,Memory Usage\n"
    try:
        for namespace in namespaces:
            # Fetch current metrics for all pods in the namespace
            pod_metrics = custom_api.list_namespaced_custom_object(
                group="metrics.k8s.io",
                version="v1beta1",
                namespace=namespace,
                plural="pods"
            )
            metrics_map = {item["metadata"]["name"]: item for item in pod_metrics.get("items", [])}
            pods = api_instance.list_namespaced_pod(namespace, watch=False)
            for pod in pods.items:
                pod_name = pod.metadata.name
                for container in pod.spec.containers:
                    container_name = container.name
                    pod_metric = metrics_map.get(pod_name, {})
                    container_metric = next((c for c in pod_metric.get("containers", []) if c["name"] == container_name), None)
                    cpu_usage = "N/A"
                    memory_usage = "N/A"
                    if container_metric:
                        cpu_usage = container_metric.get("usage", {}).get("cpu", "N/A")
                        memory_usage = container_metric.get("usage", {}).get("memory", "N/A")
                        # print(f"before conversion, pod_name: {pod_name}, cpu_usage: {cpu_usage}, memory_usage: {memory_usage}")
                        if cpu_usage != "N/A":
                            cpu_usage = convert_cpu_to_millicores(cpu_usage)
                        if memory_usage != "N/A":
                            memory_usage = convert_memory_to_mib(memory_usage)
                        # print(f"after conversion, pod_name: {pod_name}, cpu_usage: {cpu_usage}, memory_usage: {memory_usage}")
                    resource_allocation += f"{namespace},{pod_name},{container_name},{cpu_usage},{memory_usage}\n"
    except Exception as e:
        print(f"Error: {e}")

    return resource_allocation

def record_pod_resource_usage(wrk_log_path, target_cluster_rps):
    if target_cluster_rps == 0:
        return
    with open(wrk_log_path, "a") as f:
        f.write("\n-- start of resource usage --\n")
        resource_usage = get_pod_resource_usage()
        f.write(resource_usage)
        f.write("-- end of resource usage --\n\n")

inter_cluster_latency = dict()
inter_cluster_latency["node1"] = dict()
inter_cluster_latency["node2"] = dict()
inter_cluster_latency["node3"] = dict()
inter_cluster_latency["node4"] = dict()

inter_cluster_latency["node1"]["node2"] = 20 # west east
inter_cluster_latency["node1"]["node3"] = 0 # west, central
inter_cluster_latency["node1"]["node4"] = 0 # west, south 
inter_cluster_latency["node2"]["node3"] = 0 # east, central
inter_cluster_latency["node2"]["node4"] = 0 # east, south
inter_cluster_latency["node3"]["node4"] = 0 # central, south

inter_cluster_latency["node1"]["node1"] = 0 # west, west
inter_cluster_latency["node2"]["node2"] = 0 # central, central
inter_cluster_latency["node3"]["node3"] = 0 # south, south
inter_cluster_latency["node4"]["node4"] = 0 # east, east

node_to_region = {"node1":"us-west-1", "node2":"us-east-1", "node3":"us-central-1", "node4":"us-south-1"}

CONFIG = dict()
CONFIG["mode"] = "runtime"

CONFIG["routing_rule"] = "SLATE"
# CONFIG["routing_rule"] = "WATERFALL2"

CONFIG["distribution"] = "exp"
CONFIG["thread"] = 100
CONFIG["connection"] = 100
CONFIG["duration"] = 60
CONFIG["west_write10kb_RPS"] = 200
CONFIG["west_write1mb_RPS"] = 200
CONFIG["east_write10kb_RPS"] = 100
CONFIG["east_write1mb_RPS"] = 100
CONFIG["traffic_segmentation"] = 1

for src_node in inter_cluster_latency:
    for dst_node in inter_cluster_latency[src_node]:
        src_region = node_to_region[src_node]
        dst_region = node_to_region[dst_node]
        CONFIG[f"inter_cluster_latency,{src_region},{dst_region}"] = inter_cluster_latency[src_node][dst_node]
        CONFIG[f"inter_cluster_latency,{dst_region},{src_region}"] = inter_cluster_latency[src_node][dst_node]
        
CONFIG["benchmark_name"] = "usecase3-compute-diff"
CONFIG["total_num_services"] = 2
if CONFIG["routing_rule"] == "SLATE":
    CONFIG["capacity"] = 100000
else:
    CONFIG["capacity"] = 700
CONFIG["degree"] = 2


success, nodename = run_command("kubectl get nodes | grep 'node1' | awk '{print $1}'")
success, ingressgw_http2_nodeport = run_command("kubectl get svc istio-ingressgateway -n istio-system -o=json | jq '.spec.ports[] | select(.name==\"http2\") | .nodePort'")
server_ip = f"http://{nodename}:{ingressgw_http2_nodeport}"
west_cluster="west"
east_cluster="east"
wrk_command_list = [
    
    f'./wrk -D {CONFIG["distribution"]} -t{CONFIG["thread"]} -c{CONFIG["connection"]} -d{CONFIG["duration"]} -L -S -s ./{west_cluster}_write10kb.lua {server_ip} -R{CONFIG["west_write10kb_RPS"]} | grep -v "Thread calibration" >> {west_cluster}_write10kb.wrklog', \
    
    f'./wrk -D {CONFIG["distribution"]} -t{CONFIG["thread"]} -c{CONFIG["connection"]} -d{CONFIG["duration"]} -L -S -s ./{west_cluster}_write1mb.lua {server_ip} -R{CONFIG["west_write1mb_RPS"]} | grep -v "Thread calibration" >> {west_cluster}_write1mb.wrklog', \
    
    f'./wrk -D {CONFIG["distribution"]} -t{CONFIG["thread"]} -c{CONFIG["connection"]} -d{CONFIG["duration"]} -L -S -s ./{east_cluster}_write10kb.lua {server_ip} -R{CONFIG["east_write10kb_RPS"]} | grep -v "Thread calibration" >> {east_cluster}_write10kb.wrklog', \
    
    f'./wrk -D {CONFIG["distribution"]} -t{CONFIG["thread"]} -c{CONFIG["connection"]} -d{CONFIG["duration"]} -L -S -s ./{east_cluster}_write1mb.lua {server_ip} -R{CONFIG["east_write1mb_RPS"]} | grep -v "Thread calibration" >> {east_cluster}_write1mb.wrklog', \
    
]

def wait_for_pods():
    while True:
        if are_all_pods_ready():
            break
        print("Waiting for all pods to be ready")
        time.sleep(1)
    print("All pods are ready")
    
wait_for_pods()
local_env_file = update_env_txt(CONFIG)
kubectl_cp_from_host_to_slate_controller_pod(local_env_file, "/app/env.txt")
time.sleep(1)

kubectl_cp_from_host_to_slate_controller_pod(f"usecase3-compute-diff-ts-{CONFIG['traffic_segmentation']}-trace.csv", "/app/trace.csv")
t=10
print(f"sleep for {t} seconds to wait for the training to be done in global controller")
for i in range(t):
    time.sleep(1)
    print(f"start in {t-i} seconds")

with concurrent.futures.ThreadPoolExecutor() as executor:
    future_list = list()
    for wrk_cmd in wrk_command_list:
        future_list.append(executor.submit(run_command, wrk_cmd))
    for future in concurrent.futures.as_completed(future_list):
        print(future.result())
    
    ''' record resource allocation '''
    time.sleep(1)
    for cluster in wrk_log_path_dict:
        record_pod_resource_allocation(wrk_log_path_dict[cluster], rps_dict[cluster])
        
    ''' record resource usage 20 before the end of the experiment '''
    sleep_before_resource_usage_recording = CONFIG['duration'] - 10
    time.sleep(sleep_before_resource_usage_recording)
    print(f"sleep for {sleep_before_resource_usage_recording} seconds before resource resource usage")
    for cluster in wrk_log_path_dict:
        record_pod_resource_usage(wrk_log_path_dict[cluster], rps_dict[cluster])
        
    ''' Join all threads '''
    for future in concurrent.futures.as_completed(future_list):
        print(future.result())
print("Both wrk2 have completed.")

flist = ["/app/endpoint_rps_history.csv"]
for src_in_pod in flist:
    dst_in_host = f'{output_dir}/{routing_rule}-{src_in_pod.split("/")[-1]}'
    kubectl_cp_from_slate_controller_to_host(src_in_pod, dst_in_host)
    # run_command(f"python plot_rps.py {dst_in_host}")
if mode == "profile":
    src_in_pod = "/app/trace_string.csv"
    dst_in_host = f"{output_dir}/trace.slatelog"
    kubectl_cp_from_slate_controller_to_host(src_in_pod, dst_in_host)
elif mode == "runtime":
    src_in_pod = "/app/error.log"
    dst_in_host = f'{output_dir}/{routing_rule}-{src_in_pod.split("/")[-1]}'
    kubectl_cp_from_slate_controller_to_host(src_in_pod, dst_in_host)
    
    flist = ["/app/routing_history.csv", "/app/endpoint_rps_history.csv"]
    for src_in_pod in flist:
        dst_in_host = f'{output_dir}/{routing_rule}-{src_in_pod.split("/")[-1]}'
        kubectl_cp_from_slate_controller_to_host(src_in_pod, dst_in_host)
        
    # if routing_rule == "WATERFALL":
    #     src_in_pod = "/app/alternative_routing_history.csv"
    #     dst_in_host = f'{output_dir}/{routing_rule}-{src_in_pod.split("/")[-1]}'
    #     kubectl_cp_from_slate_controller_to_host(src_in_pod, dst_in_host)
        
    if routing_rule == "WATERFALL" or routing_rule == "SLATE" or routing_rule == "WATERFALL2":
        ## copy latency function pdf files for debugging purpose
        plt_file_list = list()
        for svc in ["frontend", "a", "b", "c"]:
            plt_file_list.append(f"latency-{svc}.pdf")
        for file in plt_file_list:
            src_in_pod = f"/app/{file}"
            dst_in_host = f"{output_dir}/latency_function/{routing_rule}-{file}"
            kubectl_cp_from_slate_controller_to_host(src_in_pod, dst_in_host)
            
        # pct_flist = list()                                    
        # for svc in ["frontend", "a", "b"]:
        #     pct_flist.append(f"percentage_df-{svc}.csv")
        # for file in pct_flist:
        #     src_in_pod = f"/app/{file}"
        #     dst_in_host = f"{output_dir}/{routing_rule}-{file}"
        #     kubectl_cp_from_slate_controller_to_host(src_in_pod, dst_in_host)
            
        other_file_list = ["coefficient.csv", "env.txt"] # "constraint.csv", "variable.csv", "network_df.csv", "compute_df.csv"
        for file in other_file_list:
            src_in_pod = f"/app/{file}"
            dst_in_host = f"{output_dir}/{routing_rule}-{file}"
            kubectl_cp_from_slate_controller_to_host(src_in_pod, dst_in_host)
else:
    print(f"mode: {mode} is not supported")
    assert False
'''end of one set of experiment'''
restart_deploy(exclude=[])