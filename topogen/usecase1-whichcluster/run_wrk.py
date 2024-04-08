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

def parse_xml(file_path):
    tree = ET.parse(file_path)
    return tree.getroot()


def get_nodename_and_ipaddr(file_path):
    node_dict = dict()
    namespaces = {
        'ns': 'http://www.geni.net/resources/rspec/3',
    }
    # Load and parse the XML file
    tree = ET.parse(file_path)
    root =  tree.getroot()
    # Extract node names and their IPv4 addresses
    nodes = root.findall('.//ns:node', namespaces)
    nodes_info = [
        (
            node.get('client_id'),
            # node.find('.//ns:host', namespaces).get('name'),
            [login.get('hostname') for login in node.findall('.//ns:services/ns:login', namespaces)][0],
            node.find('.//ns:host', namespaces).get('ipv4')
        )
        for node in nodes if node.find('.//ns:host', namespaces) is not None
    ]
    for node, hostname, ipaddr in nodes_info:
        node_dict[node] = {"hostname": hostname, "ipaddr": ipaddr}
    return node_dict

node_dict = get_nodename_and_ipaddr(CLOUDLAB_CONFIG_XML)
for node in node_dict:
    print(f"node: {node}, hostname: {node_dict[node]['hostname']}, ipaddr: {node_dict[node]['ipaddr']}")

assert len(node_dict) > 0

def pkill_background_noise(node_dict):
    for node in node_dict:
        pkill_command = 'pkill -f background-noise'
        run_command(f"ssh gangmuk@{node_dict[node]['hostname']} {pkill_command}", required=False, print_error=False)
        print(f"{pkill_command} in {node_dict[node]['hostname']}")
        
def delete_tc_rule_in_client(node_dict):
    for node in node_dict:
        run_command(f"ssh gangmuk@{node_dict[node]['hostname']} sudo tc qdisc del dev eno1 root", required=False, print_error=False)
        print(f"delete tc qdisc rule in {node_dict[node]['hostname']}")

# Execute this function to clean up resources in case of a crash
def cleanup_on_crash():
    print("Cleaning up resources...")
    delete_tc_rule_in_client(node_dict)
    pkill_background_noise(node_dict)
    
# Signal handler
def signal_handler(signum, frame):
    print(f"Received signal: {signum}")
    cleanup_on_crash()
    sys.exit(1)
    
# Exception handler
def handle_exception(exc_type, exc_value, exc_traceback):
    print("Unhandled exception:", exc_info=True)
    cleanup_on_crash()
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    
# register this function to be called upon normal termination or unhandled exceptions. But it will not handle termination signals like SIGKILL or SIGTERM.
atexit.register(cleanup_on_crash)


sys.excepthook = handle_exception # Override the default exception hook
# signal.signal(signal.SIGTERM, signal_handler) # Register the signal handler for SIGTERM
# signal.signal(signal.SIGINT, signal_handler) # keyboard interrrupt


def get_pod_name_from_deploy(deployment_name, namespace='default'):
    config.load_kube_config()
    api_instance = client.AppsV1Api()
    try:
        success, pod_name = run_command(f"kubectl get pods -l app={deployment_name} -o custom-columns=:metadata.name")
        return pod_name
    except client.ApiException as e:
        print(f"Error fetching the pod name for deployment {deployment_name}: {e}")
        assert False
        
def check_file_exists_in_pod(pod_name, namespace, file_path):
    command = f"kubectl exec {pod_name} --namespace {namespace} -- sh -c '[ -f {file_path} ] && echo Exists || echo Does not exist'"
    success, ret = run_command(command, required=False)
    return success

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

def kubectl_cp_from_host_to_slate_controller_pod(src_in_host, dst_in_pod):
    success, slate_controller_pod = run_command("kubectl get pods -l app=slate-controller -o custom-columns=:metadata.name")
    # print(f"Try kubectl_cp_from_host_to_slate_controller_pod")
    print(f"- src_in_host: {src_in_host}")
    print(f"- dst_in_pod: {slate_controller_pod}:{dst_in_pod}")
    run_command(f"kubectl cp {src_in_host} {slate_controller_pod}:{dst_in_pod}")
    print(f"finish scp from {src_in_host} to {slate_controller_pod}:{dst_in_pod}")
    

def update_env_txt(config, mode, benchmark_name, total_num_services, routing_rule, rps_dict, inter_cluster_latency, node_to_region, capacity, degree):
    print("update_env_txt")
    config["mode"] = mode
    config["routing_rule"] = routing_rule
    for cluster, rps in rps_dict.items():
        config[f"{cluster}_RPS"] = rps
    for src_node in inter_cluster_latency:
        for dst_node in inter_cluster_latency[src_node]:
            # NOTE: it is divided by 2 for oneway.
            src_region = node_to_region[src_node]
            dst_region = node_to_region[dst_node]
            config[f"inter_cluster_latency,{src_region},{dst_region}"] = inter_cluster_latency[src_node][dst_node]
            config[f"inter_cluster_latency,{dst_region},{src_region}"] = inter_cluster_latency[src_node][dst_node]
    config["benchmark_name"] = benchmark_name
    config["total_num_services"] = total_num_services
    config["capacity"] = capacity
    config["degree"] = degree
   # File to update
    local_env_file = "local_env.txt"
    with open(local_env_file, "w") as file:
        for key, value in config.items():
            file.write(f"{key},{value}\n") 
    print(f"write {local_env_file}")
    return local_env_file

def convert_memory_to_mib(memory_usage):
    # Convert memory usage to MiB
    unit = memory_usage[-2:]  # Extract the unit (Ki, Mi, Gi)
    value = int(memory_usage[:-2])  # Extract the numeric value
    converted_value = 0
    if unit == "Ki":
        converted_value = value / 1024  # 1 MiB = 1024 KiB
    elif unit == "Mi":
        converted_value = value
    elif unit == "Gi":
        converted_value = value * 1024  # 1 GiB = 1024 MiB
    else:
        converted_value = value / (1024**2)  # Assume the value is in bytes if no unit
    return int(converted_value)

def convert_cpu_to_millicores(cpu_usage):
    converted_value = 0
    # Convert CPU usage to millicores
    if cpu_usage.endswith('n'):  # nanocores
        converted_value = int(cpu_usage.rstrip('n')) / 1000000
    elif cpu_usage.endswith('u'):  # assuming 'u' to be a unit close to millicores
        converted_value = int(cpu_usage.rstrip('u')) / 1000  # Convert assuming 'u' represents microcores
    else:
        converted_value = int(cpu_usage)  # Assuming direct millicore value
    return int(converted_value)

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

def get_pod_resource_allocation(namespace='default'):
    config.load_kube_config()
    api_instance = client.CoreV1Api()
    namespaces = ["default", "istio-system"]
    resource_allocation = "Namespace,Resource Type,Pod Name,Container Name,CPU Limit,CPU Request,Memory Limit,Memory Request\n"
    try:
        for namespace in namespaces:
            pods = api_instance.list_namespaced_pod(namespace, watch=False)
            for pod in pods.items:
                metadata = pod.metadata
                for container in pod.spec.containers:
                    # Fetch resource requests and limits
                    resources = container.resources
                    limits = resources.limits or {}
                    requests = resources.requests or {}

                    cpu_limit = limits.get("cpu", "N/A")
                    cpu_request = requests.get("cpu", "N/A")
                    mem_limit = limits.get("memory", "N/A")
                    mem_request = requests.get("memory", "N/A")

                    resource_allocation += f"{namespace},Pod,{metadata.name},{container.name},{cpu_limit},{cpu_request},{mem_limit},{mem_request}\n"
    except Exception as e:
        print(f"Error: {e}")
    return resource_allocation

def record_pod_resource_allocation(wrk_log_path, target_cluster_rps):
    if target_cluster_rps == 0:
        return
    with open(wrk_log_path, "a") as f:
        f.write("\n-- start of resource allocation --\n")
        resource_allocation = get_pod_resource_allocation()
        f.write(resource_allocation)
        f.write("-- end of resource allocation --\n")
        

def record_pod_resource_usage(wrk_log_path, target_cluster_rps):
    if target_cluster_rps == 0:
        return
    with open(wrk_log_path, "a") as f:
        f.write("\n-- start of resource usage --\n")
        resource_usage = get_pod_resource_usage()
        f.write(resource_usage)
        f.write("-- end of resource usage --\n\n")
        

def run_wrk(copy_config, target_cluster, req_type, target_cluster_rps, wrk_log_path):
    assert target_cluster_rps >= 0
    if target_cluster_rps == 0:
        msg = f"{target_cluster} {req_type} {target_cluster_rps} RPS is skipped"
        print(msg)
        return msg
    success, nodename = run_command("kubectl get nodes | grep 'node1' | awk '{print $1}'")
    success, ingressgw_http2_nodeport = run_command("kubectl get svc istio-ingressgateway -n istio-system -o=json | jq '.spec.ports[] | select(.name==\"http2\") | .nodePort'")
    server_ip = f"http://{nodename}:{ingressgw_http2_nodeport}"
    
    
    print("overwrite connection and thread")
    copy_config["connection"] = target_cluster_rps
    # if copy_config["connection"] > target_cluster_rps:
    #     # copy_config["connection"] = min(copy_config["connection"], target_cluster_rps)
    #     copy_config["connection"] = target_cluster_rps
    #     if copy_config["connection"] < 0:
    #         copy_config["connection"] = target_cluster_rps
    
    
    # if copy_config["connection"] > 200:
        # copy_config["thread"] = copy_config["connection"] - 100
    copy_config["thread"] = copy_config["connection"]
    
    # if target_cluster_rps == 400:
    #     copy_config["thread"] = 200
    #     copy_config["connection"] = 300
    # if target_cluster_rps == 500:
    #     copy_config["thread"] = 300
    #     copy_config["connection"] = 400
    # if target_cluster_rps == 600:
    #     copy_config["thread"] = 400
    #     copy_config["connection"] = 500
    # if target_cluster_rps >= 500:
    #     copy_config["thread"] = 500
    #     copy_config["connection"] = 800
    
    
    # safety check
    if copy_config["thread"] > copy_config["connection"]:
        copy_config["thread"] = min(copy_config["thread"], copy_config["connection"])
        
    print(f"rps: {target_cluster_rps}")
    print(f"connection: {copy_config['connection']}")
    print(f"thread: {copy_config['thread']}")
    copy_config["cluster"] = target_cluster
    copy_config["RPS"] = target_cluster_rps
    
    # print(f'start {req_type} RPS {target_cluster_rps} to {target_cluster} cluster for {copy_config["duration"]} seconds')
    with open(wrk_log_path, "w") as f:
        info = "-- start of config --\n"
        for key, value in copy_config.items():
            info += f"{key},{value}\n"
        info += "-- end of config --\n\n"
        f.write(info)

    '''
    with --u_latency
    reference: https://github.com/giltene/wrk2, search for Coordinated Omission  
    '''
    # wrk_command = f'./wrk -D {copy_config["distribution"]} -t{copy_config["thread"]} -c{copy_config["connection"]} -d{copy_config["duration"]} -L -S -s  --u_latency./{target_cluster}_{req_type}.lua {server_ip} -R{target_cluster_rps} >> {wrk_log_path}'
    
    print("-"*50)
    print(f"{wrk_log_path}")
    print("-"*50)
    # run_command("./curl.sh west")
    wrk_command = f'./wrk -D {copy_config["distribution"]} -t{copy_config["thread"]} -c{copy_config["connection"]} -d{copy_config["duration"]} -L -S -s ./{target_cluster}_{req_type}.lua {server_ip} -R{target_cluster_rps} | grep -v "Thread calibration" >> {wrk_log_path}'
    run_command(wrk_command)
    
    
    return f"{target_cluster} {req_type} {target_cluster_rps} RPS is done"

def sleep_and_print(sl):
    print(f"@@ sleep {sl} seconds")
    run_command(f"sleep {sl}")

def disable_istio():
    run_command("kubectl label namespace default istio-injection=disabled")
    print("@@ kubectl label namespace default istio-injection=disabled")
    sleep_and_print(10)

def enable_istio():
    run_command("kubectl label namespace default istio-injection=enabled")
    print("@@ kubectl label namespace default istio-injection=enabled")
    sleep_and_print(10)

def delete_wasm():
    run_command("kubectl delete -f ../wasmplugins.yaml")
    restart_deploy()
    print("@@ kubectl delete -f ../wasmplugins.yaml")


def apply_wasm():
    run_command("kubectl apply -f ../wasmplugins.yaml")
    print("@@ kubectl apply -f ../wasmplugins.yaml")
    sleep_and_print(5)

def restart_wasm():
    delete_wasm()
    apply_wasm()

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

def restart_deploy(exclude=[]):
    print("start restart deploy")
    config.load_kube_config()
    api_instance = client.AppsV1Api()
    # excluded_deployment_name = "slate-controller"
    try:
        deployments = api_instance.list_namespaced_deployment(namespace="default")
        for deployment in deployments.items:
            if deployment.metadata.name not in exclude:
                run_command(f"kubectl rollout restart deploy {deployment.metadata.name}")
    except client.ApiException as e:
        print("Exception when calling AppsV1Api->list_namespaced_deployment: %s\n" % e)
        
    while True:
        if are_all_pods_ready():
            break
        time.sleep(1)
    time.sleep(5)
    print("restart deploy is done")

def restart_slate_controller():
    run_command("kubectl rollout restart deploy slate-controller")
    print("@@ kubectl rollout restart deploy slate-controller")
    sleep_and_print(10)


def add_latency_rules(src_host, interface, dst_node_ip, delay):
    if delay == 0:
        print(f"skip add_latency_rules, delay: {delay}")
        return
    class_id = f"1:{delay}"
    handle_id = delay
    run_command(f'ssh gangmuk@{src_host} sudo tc class add dev {interface} parent 1: classid {class_id} htb rate 100mbit', required=False, print_error=False)
    run_command(f'ssh gangmuk@{src_host} sudo tc qdisc add dev {interface} parent {class_id} handle {handle_id}: netem delay {delay}ms', required=False, print_error=False)
    run_command(f'ssh gangmuk@{src_host} sudo tc filter add dev {interface} protocol ip parent 1:0 prio 1 u32 match ip dst {dst_node_ip} flowid {class_id}')


def start_background_noise(node_dict, cpu_noise=30):
    for node in node_dict:
        if node == "node0" or node == "node5":
            print("skip start_background_noise in node0. node0 is control plane node")
            continue
        # print(f"Try to run background-noise -cpu={cpu_noise} in {node_dict[node]['hostname']}")
        run_command(f"ssh gangmuk@{node_dict[node]['hostname']} 'nohup /users/gangmuk/projects/slate-benchmark/background-noise/background-noise -cpu={cpu_noise} > /dev/null 2>&1 &'", nonblock=False)
        print(f"background-noise -cpu={cpu_noise} in {node_dict[node]['hostname']}")


def main():
    dir_name = sys.argv[1]
    if len(sys.argv) != 2:
        print("Usage: python run_wrk.py <dir_name>\nexit...")
        exit()
    
    start_time = datetime.now()
    
    ########################################################
    CONFIG = {
        'distribution': 'exp',
        'thread': 100, # min(thread, connection, rps-50)
        'connection': 200, # min(connection, rps-50)
        'duration': 60,
        # 'cpu_noise': 50
        'cpu_noise': 70
    }
    benchmark_name="usecase1-whichcluster" # a,b, 1MB and c 2MB file write
    total_num_services=5
    # capacity = 265 # 5ms, 400RPS 
    # capacity = 365 # 50ms, 400RPS
    # capacity = 310 # 5ms, 500RPS
    # capacity = 380 # 50ms, 500RPS 
    # capacity = 400
    capacity = 300
    degree = 2
    mode_set = ["profile", "runtime"]
    mode_and_routing_rule = {\
        # "profile": ["LOCAL"],\
        # "runtime": ["SLATE"],\
        # "runtime": ["WATERFALL2"],\
        "runtime": ["SLATE", "WATERFALL2"],\
        # "runtime": ["WATERFALL2"],\
        # "runtime": ["WATERFALL", "SLATE"],\
        # "runtime": ["LOCAL", "SLATE", "MCLB",  "WATERFALL"],\
        # "runtime": ["LOCAL", "SLATE", "MCLB",  "WATERFALL", "REMOTE"],\
    }
    
    ## for experiment
    all_RPS_list = [ \
                    ## profile
                    # {"west": 100}, \
                    # {"west": 200}, \
                    # {"west": 300}, \
                    # {"west": 400}, \
                    # {"west": 500}, \
                    
                    # {"west":500, "central":200, "east": 500, "south":50}, \
                    {"west":400, "central":100, "east": 400, "south":50}, \
                    ]
    
    for mode in mode_and_routing_rule:
        assert mode in mode_set
    
        
    pkill_background_noise(node_dict)
    start_background_noise(node_dict, CONFIG['cpu_noise'])
        
    node_to_region = {"node1":"us-west-1", "node2":"us-east-1", "node3":"us-central-1", "node4":"us-south-1"}
    
    inter_cluster_latency = dict()
    for src_node in node_to_region:
        inter_cluster_latency[src_node] = dict()
    
    dir_name = f"{dir_name}"
    inter_cluster_latency["node1"]["node2"] = 10 # west east
    inter_cluster_latency["node1"]["node3"] = 5 # west, central
    inter_cluster_latency["node1"]["node4"] = 5 # west, south 
    inter_cluster_latency["node2"]["node3"] = 10 # east, central
    inter_cluster_latency["node2"]["node4"] = 10 # east, south
    inter_cluster_latency["node3"]["node4"] = 5 # central, south
    
    inter_cluster_latency["node1"]["node1"] = 0 # west, west
    inter_cluster_latency["node2"]["node2"] = 0 # central, central
    inter_cluster_latency["node3"]["node3"] = 0 # south, south
    inter_cluster_latency["node4"]["node4"] = 0 # east, east

    for src_node in inter_cluster_latency:
        for dst_node in inter_cluster_latency[src_node]:
            if src_node == dst_node:
                continue
            inter_cluster_latency[dst_node][src_node] = inter_cluster_latency[src_node][dst_node]
    print("inter_cluster_latency")
    pprint(inter_cluster_latency)
    
    delete_tc_rule_in_client(node_dict)
    
    interface = "eno1"  # Ensure this is the correct interface
    # inter_cluster_latency["node1"]["node2"] = 40
    for src_node in inter_cluster_latency:
        src_host = node_dict[src_node]['hostname']
        run_command(f'ssh gangmuk@{src_host} sudo tc qdisc add dev {interface} root handle 1: htb')
        for dst_node in inter_cluster_latency[src_node]:
            if src_node == dst_node:
                continue
            dst_node_ip = node_dict[dst_node]['ipaddr'] 
            delay = inter_cluster_latency[src_node][dst_node]
            add_latency_rules(src_host, interface, dst_node_ip, delay)
            print(f"Added {delay}ms from {src_host}({src_node}) to {dst_node_ip}({dst_node})")
    ######################################################################################################
    # for node in node_dict:
    #     run_command(f"ssh gangmuk@{node_dict[node]['hostname']} ~/projects/slate-benchmark/background-noise/background-noise -cpu=30")
    #     print(f"start background-noise in {node_dict[node]['hostname']}")
    req_type_list = ["get_metric"] # It should match wrk2 lua script
    while True:
        if are_all_pods_ready():
            break
        print("Waiting for all pods to be ready")
        time.sleep(1)
    print("All pods are ready")
    for mode in mode_and_routing_rule:
        for rps_dict in all_RPS_list:
            print(f"dir name: {dir_name}")
            for req_type in req_type_list:
                for routing_rule in mode_and_routing_rule[mode]:
                    per_wrk_st = datetime.now()
                    ''' Initialize the output path for different logs'''
                    output_dir = f"{dir_name}/"
                    for cluster in rps_dict:
                        # cluster[0]: either 'w' or 'e' or 'c'
                        output_dir += f"{cluster[0]}{rps_dict[cluster]}"
                    # e.g., output_dir: get_metric-ww-Mar13_testing/w200e100
                    assert output_dir != ""
                    if not os.path.isdir(output_dir):
                        os.makedirs(output_dir)
                    if not os.path.isdir(f"{output_dir}/latency_function"):
                        os.makedirs(f"{output_dir}/latency_function")
                    wrk_log_path_dict = dict()
                    for cluster in rps_dict:
                        wrk_log_path_dict[cluster] = f"{output_dir}/{routing_rule}-{mode}-c{CONFIG['cpu_noise']}-d{degree}-R{rps_dict[cluster]}-{cluster}.wrklog"
                    
                    def recalculate_capacity(capacity, rps_dict):
                        total_capacity = capacity * len(rps_dict)
                        total_demand = sum(rps_dict.values())
                        if total_demand > total_capacity:
                            return total_demand // len(rps_dict)
                        else:
                            return capacity
                    recalculated_capacity = recalculate_capacity(capacity, rps_dict)
                    print(f"** recalculated_capacity: {recalculated_capacity}")
                    ''' update env.txt and scp to slate-controller pod '''
                    local_env_file = update_env_txt(CONFIG, mode, benchmark_name, total_num_services, routing_rule, rps_dict, inter_cluster_latency, node_to_region, recalculated_capacity, degree)
                    kubectl_cp_from_host_to_slate_controller_pod(local_env_file, "/app/env.txt")
                    if mode == "runtime":
                        slatelog = f"{benchmark_name}-trace.csv"
                        kubectl_cp_from_host_to_slate_controller_pod(slatelog, "/app/trace.csv")
                        t=20
                        print(f"sleep for {t} seconds to wait for the training to be done in global controller")
                        for i in range(t):
                            time.sleep(1)
                            print(f"start in {t-i} seconds")
                    
                    
                    # while True:
                    #     training_done = kubectl_cp_from_slate_controller_to_host("/app/train_done.txt", f"{output_dir}/train_done.txt")
                    #     if training_done:
                    #         break
                    #     print("Waiting for training to be done")
                    #     time.sleep(1)
                    
                    # This is only for debugging to confirm that env.txt is transferred to the slate-controller pod correctly by copying back from slate-controller pod to the host                            
                    # for cluster in wrk_log_path_dict:
                    #     kubectl_cp_from_slate_controller_to_host("/app/env.txt", f"temp-env-{cluster}.txt")
                    # time.sleep(1)
                    
                    ''' start to send load concurrently to all clusters'''
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        for cluster in wrk_log_path_dict:
                            print(f"cluster: {cluster}, req_type: {req_type}, RPS: {rps_dict[cluster]}")
                            # print(f"wrk_log_path: {wrk_log_path_dict[cluster]}")
                        copied_config = dict()
                        for cluster in wrk_log_path_dict:
                            copied_config[cluster] = copy.deepcopy(CONFIG)
                        future_list = list()
                        for cluster in wrk_log_path_dict:
                            future_list.append(executor.submit(run_wrk, copied_config[cluster], cluster, req_type, rps_dict[cluster], wrk_log_path_dict[cluster]))
                            time.sleep(1)
                        
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
                        print("???")
                        print(f"mode: {mode} is not supported")
                        exit()
                    '''end of one set of experiment'''
                    restart_deploy(exclude=[])
                    # restart_deploy(exclude=['slate-controller'])
                    
                    per_wrk_et = datetime.now()
                    per_wk_duration = (per_wrk_et - per_wrk_st).seconds
                    print(f"@@ per_wk_duration: {per_wk_duration} seconds")
            end_time = datetime.now()
            duration = (end_time - start_time).seconds
            print(f"@@ Total runtime: {duration} seconds")
            
    # run_command("bash ../delete_node_level_tc_qdisc.sh")
    # for node in node_dict:
    #     run_command(f"ssh gangmuk@{node_dict[node]['hostname']} pkill background-nois")
    #     print(f"start background-noise in {node_dict[node]['hostname']}")
    
    for node in node_dict:
        run_command(f"ssh gangmuk@{node_dict[node]['hostname']} sudo tc qdisc del dev eno1 root", required=False, print_error=False)
        print(f"delete tc qdisc rule in {node_dict[node]['hostname']}")
            
if __name__ == "__main__":
    main()
