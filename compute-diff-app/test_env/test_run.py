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

CONFIG = dict()
CONFIG["mode"] = "runtime"
CONFIG["routing_rule"] = "SLATE"
CONFIG["distribution"] = "exp"
CONFIG["thread"] = 100
CONFIG["connection"] = 100
CONFIG["duration"] = 60

CONFIG["west_write1kb_RPS"] = 100
CONFIG["west_write1mb_RPS"] = 100
CONFIG["east_write1kb_RPS"] = 100
CONFIG["east_write1mb_RPS"] = 100

inter_cluster_latency = dict()
inter_cluster_latency["node1"] = dict()
inter_cluster_latency["node2"] = dict()
inter_cluster_latency["node3"] = dict()
inter_cluster_latency["node4"] = dict()

inter_cluster_latency["node1"]["node2"] = 0 # west east
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
for src_node in inter_cluster_latency:
    for dst_node in inter_cluster_latency[src_node]:
        src_region = node_to_region[src_node]
        dst_region = node_to_region[dst_node]
        CONFIG[f"inter_cluster_latency,{src_region},{dst_region}"] = inter_cluster_latency[src_node][dst_node]
        CONFIG[f"inter_cluster_latency,{dst_region},{src_region}"] = inter_cluster_latency[src_node][dst_node]
        
CONFIG["benchmark_name"] = "usecase3-compute-diff"
CONFIG["total_num_services"] = 2
CONFIG["capacity"] = 100000
CONFIG["degree"] = 2


# curl_command_list = ['./curl.sh west write1kb', './curl.sh west write1mb', './curl.sh east write1kb', './curl.sh east write1mb']

success, nodename = run_command("kubectl get nodes | grep 'node1' | awk '{print $1}'")
success, ingressgw_http2_nodeport = run_command("kubectl get svc istio-ingressgateway -n istio-system -o=json | jq '.spec.ports[] | select(.name==\"http2\") | .nodePort'")
server_ip = f"http://{nodename}:{ingressgw_http2_nodeport}"
west_write1kb_RPS=1000
west_write1mb_RPS=100
east_write1kb_RPS=1000
east_write1mb_RPS=100
west_cluster="west"
east_cluster="east"
wrk_command_list = [
    
    f'./wrk -D {CONFIG["distribution"]} -t{CONFIG["thread"]} -c{CONFIG["connection"]} -d{CONFIG["duration"]} -L -S -s ./{west_cluster}_write10kb.lua {server_ip} -R{west_write1kb_RPS} | grep -v "Thread calibration" >> {west_cluster}_write10kb.wrklog', \
    
    f'./wrk -D {CONFIG["distribution"]} -t{CONFIG["thread"]} -c{CONFIG["connection"]} -d{CONFIG["duration"]} -L -S -s ./{west_cluster}_write1mb.lua {server_ip} -R{west_write1mb_RPS} | grep -v "Thread calibration" >> {west_cluster}_write1mb.wrklog', \
    
    f'./wrk -D {CONFIG["distribution"]} -t{CONFIG["thread"]} -c{CONFIG["connection"]} -d{CONFIG["duration"]} -L -S -s ./{east_cluster}_write10kb.lua {server_ip} -R{east_write1kb_RPS} | grep -v "Thread calibration" >> {east_cluster}_write10kb.wrklog', \
    
    f'./wrk -D {CONFIG["distribution"]} -t{CONFIG["thread"]} -c{CONFIG["connection"]} -d{CONFIG["duration"]} -L -S -s ./{east_cluster}_write1mb.lua {server_ip} -R{east_write1mb_RPS} | grep -v "Thread calibration" >> {east_cluster}_write1mb.wrklog', \
    
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

kubectl_cp_from_host_to_slate_controller_pod("usecase3-compute-diff-trace.csv", "/app/trace.csv")
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