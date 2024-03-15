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

sys.path.append('/users/gangmuk/projects/SLATE/global-controller')
import config as cfg

# Config
CONFIG = {
    'distribution': 'exp',
    'thread': 50,
    'connection': 50,
    'duration': 60
}

def get_pod_name_from_deploy(deployment_name, namespace='default'):
    config.load_kube_config()
    api_instance = client.AppsV1Api()
    try:
        pod_name = run_command(f"kubectl get pods -l app={deployment_name} -o custom-columns=:metadata.name")
        return pod_name
    except client.ApiException as e:
        print(f"Error fetching the pod name for deployment {deployment_name}: {e}")
        assert False
        
def check_file_exists_in_pod(pod_name, namespace, file_path):
    command = f"kubectl exec {pod_name} --namespace {namespace} -- sh -c '[ -f {file_path} ] && echo Exists || echo Does not exist'"
    success = run_command(command, required=False)
    return success

def kubectl_cp_from_slate_controller_to_host(src_in_pod, dst_in_host):
    slate_controller_pod = get_pod_name_from_deploy("slate-controller")
    print(f"Try kubectl_cp_from_slate_controller_to_host")
    print(f"src_in_pod: {slate_controller_pod}:{src_in_pod}")
    print(f"dst_in_host: {dst_in_host}")
    if check_file_exists_in_pod(slate_controller_pod, "default", src_in_pod) == False:
        print(f"Skip scp. {src_in_pod} does not exist in the slate-controller pod")
        return
    # slate_controller_pod = run_command("kubectl get pods -l app=slate-controller -o custom-columns=:metadata.name")
    temp_file = "temp_file.txt"
    run_command(f"kubectl cp {slate_controller_pod}:{src_in_pod} {temp_file}")
    run_command(f"mv {temp_file} {dst_in_host}")
    print(f"mv {temp_file} {dst_in_host}")
    print(f"finish kubectl_cp_from_slate_controller_to_host")
    

def kubectl_cp_from_host_to_slate_controller_pod(src_in_host, dst_in_pod):
    slate_controller_pod = run_command("kubectl get pods -l app=slate-controller -o custom-columns=:metadata.name")
    print(f"Try kubectl_cp_from_host_to_slate_controller_pod")
    print(f"src_in_host: {src_in_host}")
    print(f"dst_in_pod: {slate_controller_pod}:{dst_in_pod}")
    run_command(f"kubectl cp {src_in_host} {slate_controller_pod}:{dst_in_pod}")
    print(f"finish kubectl_cp_from_host_to_slate_controller_pod")
    

def update_env_txt(mode, benchmark_name, total_num_services, routing_rule, rps_dict, inter_cluster_latency):
    print("update_env_txt")
    global CONFIG
    CONFIG["mode"] = mode
    CONFIG["routing_rule"] = routing_rule
    for cluster, rps in rps_dict.items():
        CONFIG[f"{cluster}_RPS"] = rps
    CONFIG["inter_cluster_latency"] = inter_cluster_latency
    CONFIG["benchmark_name"] = benchmark_name
    if benchmark_name == "metrics":
        CONFIG["capacity"] = 150
    else:
        CONFIG["capacity"] = 9999999999
    CONFIG["total_num_services"] = total_num_services
   # File to update
    local_env_file = "local_env.txt"
    with open(local_env_file, "w") as file:
        for key, value in CONFIG.items():
            file.write(f"{key},{value}\n") 
    print(f"write {local_env_file}")
    return local_env_file
        
'''
slate_controller/app/env.txt => local file
'''
# def scp_env_txt(output_path):
    # print(f"start scp_env_txt")
    # slate_controller_pod = run_command("kubectl get pods -l app=slate-controller -o custom-columns=:metadata.name")
    # src_path = "/app/env.txt"
    # temp_file = "temp_env.txt" # This is for debugging. 
    # run_command(f"kubectl cp {slate_controller_pod}:{src_path} {temp_file}")
    # run_command(f"rm {temp_file}")
    # print(f"src_env_file: {slate_controller_pod}:{src_path}")
    # print(f"update {output_path} with env.txt")
    

# def scrape_resource_config():
#     config.load_kube_config()
#     api_instance = client.AppsV1Api()
#     try:cd
#         namespace = "default"
#         deployments = api_instance.list_namespaced_deployment(namespace, watch=False)
#         resource_allocation = ""
#         for deployment in deployments.items:
#             metadata = deployment.metadata
#             spec = deployment.spec.template.spec.containers[0]

#             cpu_limit = spec.resources.limits.get("cpu") if spec.resources.limits else "N/A"
#             cpu_request = spec.resources.requests.get("cpu") if spec.resources.requests else "N/A"
#             mem_limit = spec.resources.limits.get("mem") if spec.resources.limits else "N/A"
#             mem_request = spec.resources.requests.get("mem") if spec.resources.requests else "N/A"

#             resource_allocation += f"Deployment,{metadata.name}\n"
#             resource_allocation += f"CPU Limit,{cpu_limit}\n"
#             resource_allocation += f"CPU Request,{cpu_request}\n"
#             resource_allocation += f"Mem Limit,{mem_limit}\n"
#             resource_allocation += f"Mem Request,{mem_request}\n"

#     except Exception as e:
#         print(f"Error: {e}")
        
#     return resource_allocation

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
        

def run_command(command, required=True):
    """Run shell command and return its output"""
    try:
        output = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT)
        return output.decode('utf-8').strip()
    except subprocess.CalledProcessError as e:
        print(f"Error executing command: {e.output.decode('utf-8')}")
        if required:
            print("Exit...")
            exit()
        return False

def run_wrk(copy_config, target_cluster, req_type, target_cluster_rps, wrk_log_path):
    assert target_cluster_rps >= 0
    if target_cluster_rps == 0:
        msg = f"{target_cluster} {req_type} {target_cluster_rps} RPS is skipped"
        print(msg)
        return msg
    nodename = run_command("kubectl get nodes | grep 'node1' | awk '{print $1}'")
    ingressgw_http2_nodeport = run_command("kubectl get svc istio-ingressgateway -n istio-system -o=json | jq '.spec.ports[] | select(.name==\"http2\") | .nodePort'")
    server_ip = f"http://{nodename}:{ingressgw_http2_nodeport}"
    if target_cluster_rps < copy_config["connection"]:
        copy_config["connection"] = target_cluster_rps
    if copy_config["connection"] < copy_config["thread"]:
        copy_config["thread"] = copy_config["connection"]
        
    copy_config["cluster"] = target_cluster
    copy_config["RPS"] = target_cluster_rps
    
    print(f'start {req_type} RPS {target_cluster_rps} to {target_cluster} cluster for {copy_config["duration"]} seconds')
    with open(wrk_log_path, "a") as f:
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
    
    ''' without  --u_latency '''
    wrk_command = f'./wrk -D {copy_config["distribution"]} -t{copy_config["thread"]} -c{copy_config["connection"]} -d{copy_config["duration"]} -L -S -s ./{target_cluster}_{req_type}.lua {server_ip} -R{target_cluster_rps} >> {wrk_log_path}'
    run_command(wrk_command)
    
    print("-"*50)
    print(f"{wrk_log_path}")
    print("-"*50)
    
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
    print("@@ kubectl delete -f ../wasmplugins.yaml")
    sleep_and_print(5)

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
    time.sleep(15)
    print("restart deploy is done")

def restart_slate_controller():
    run_command("kubectl rollout restart deploy slate-controller")
    print("@@ kubectl rollout restart deploy slate-controller")
    sleep_and_print(10)

'''
slate_controller/app/trace_string.csv -> local file
'''
# def scp_trace_string_file(output_path):
#     print(f"start scp_trace_string_file")
#     slate_controller_pod = run_command("kubectl get pods -l app=slate-controller -o custom-columns=:metadata.name")
#     src_path = "/app/trace_string.csv"
#     print(f"src_env_file: {slate_controller_pod}:{src_path}")
#     temp_path = "temp.slatelog"
#     print(f"dst: {output_path}")
#     run_command(f"kubectl cp {slate_controller_pod}:{src_path} {temp_path}")
#     run_command(f"mv {temp_path} {output_path}")
#     print(f"scp_trace_string_file is done")
    
    

def main():
    
    dir_postfix = sys.argv[1]
    if len(sys.argv) != 2:
        print("Usage: python run_wrk.py <dir_postfix>\nexit...")
        exit()
    
    start_time = datetime.now()
    istio_config = True
    with_wasm = [True]
    # if istio_config == False:
    #     disable_istio()
    # else:
    #     enable_istio()

    ########################################################
    '''
    Experiment configurations
    It will run all combinations of the following configurations
    '''
    benchmark_name="metrics"
    total_num_services=4
    
    '''
    profile: collecting traces, routing rule is always local
    runtime: training latency functions with the given trace data (trace_string.csv)
    '''
    mode_set = ["profile", "runtime"]
    mode_and_routing_rule = {\
        "profile": ["LOCAL"],\
        # "runtime": ["WATERFALL"],\
        # "runtime": ["LOCAL", "SLATE", "MCLB",  "WATERFALL"],\
        # "runtime": ["LOCAL", "SLATE", "MCLB",  "WATERFALL", "REMOTE"],\
    }
    for mode in mode_and_routing_rule:
        assert mode in mode_set
        
    # oneway_latency = [0]
    oneway_latency = [20]
    req_type_list = ["get_metric"] # It should match wrk2 lua script
    '''
    west_rps_list["get_metrics][0], east_rps_list["get_metrics][0] are pair
    
    Similarly,
    west_rps_list["get_metrics][1], east_rps_list["get_metrics][1] are pair
    '''
    all_RPS_list = [ \
                    # {"west": 50, "east": 0}, \
                    {"west": 100, "east": 0}, \
                    # {"west": 150, "east": 0}, \
                    # {"west": 200, "east": 0}, \
                    # {"west": 250, "east": 0}, \
                    # {"west": 300, "east": 0}, \
                    # {"west": 350, "east": 0}, \
                    # {"west": 400, "east": 0}, \
                    # {"west": 450, "east": 0}, \
                    # {"west": 500, "east": 0}, \
                    ]
    ########################################################
    
    for lat in oneway_latency:
        node1_ip="128.110.96.52"
        node2_ip="128.110.96.43"
        node1_name="apt052.apt.emulab.net" # node1
        node2_name="apt043.apt.emulab.net" # node2
        run_command(f"bash ../add_node_level_latency.sh {node1_name} {node1_ip} {node2_name} {node2_ip} {lat}")
        for wasm_config in with_wasm:
            if istio_config == True:
                print(f"wasm config: {wasm_config}")
                if wasm_config:
                    # apply_wasm()
                    a=1
                else:
                    delete_wasm()
            else:
                print("istio config is false. exit... (disabling istio is not there yet.)")
                exit()
                
            # restart_deploy(exclude=[])
            print("restart deploy is done")
            for mode in mode_and_routing_rule:
                for routing_rule in mode_and_routing_rule[mode]:
                    date_ = datetime.now().strftime("%b%d")
                    postfix = f"{date_}_{dir_postfix}"
                    print(f"* postfix for output file: {postfix}")
                    for req_type in req_type_list:
                        for rps_dict in all_RPS_list:
                            per_wrk_st = datetime.now()
                            
                            ''' Initialize the output path for different logs'''
                            if istio_config:
                                if wasm_config:
                                    output_dir = f"{req_type}-ww-{postfix}"
                                else:
                                    output_dir = f"{req_type}-wow-{postfix}"
                            else:
                                output_dir = f"{req_type}-woi-{postfix}"
                            output_dir += "/"
                            for cluster in rps_dict:
                                # cluster[0]: either 'w' or 'e'
                                output_dir += f"{cluster[0]}{rps_dict[cluster]}"
                            # e.g., output_dir: get_metric-ww-Mar13_testing/w200e100
                            assert output_dir != ""
                            if not os.path.isdir(output_dir):
                                os.makedirs(output_dir)
                            formatted_datetime = datetime.now().strftime("%m-%d-%H:%M")
                            wrk_log_path_dict = dict()
                            for cluster in rps_dict:
                                wrk_log_path_dict[cluster] = f"{output_dir}/{mode}-L{lat}-{routing_rule}-R{rps_dict[cluster]}-{cluster}-{formatted_datetime}.wrklog"
                            
                            ''' update env.txt and scp to slate-controller pod '''
                            local_env_file = update_env_txt(mode, benchmark_name, total_num_services, routing_rule, rps_dict, lat)
                            kubectl_cp_from_host_to_slate_controller_pod(local_env_file, "/app/env.txt")
                            time.sleep(1)
                            # This is only for debugging to confirm that env.txt is transferred to the slate-controller pod correctly by copying back from slate-controller pod to the host                            
                            for cluster in wrk_log_path_dict:
                                kubectl_cp_from_slate_controller_to_host("/app/env.txt", f"temp-env-{cluster}.txt")
                            time.sleep(1)
                            
                            ''' start to send load concurrently to all clusters'''
                            with concurrent.futures.ThreadPoolExecutor() as executor:
                                for cluster in wrk_log_path_dict:
                                    print(f"cluster: {cluster}, req_type: {req_type}, RPS: {rps_dict[cluster]}")
                                    # print(f"wrk_log_path: {wrk_log_path_dict[cluster]}")
                                    
                                global CONFIG
                                copy_config = copy.deepcopy(CONFIG) # to avoid concurrency issue
                                future_list = list()
                                for cluster in wrk_log_path_dict:
                                    future_list.append(executor.submit(run_wrk, copy_config, cluster, req_type, rps_dict[cluster], wrk_log_path_dict[cluster]))
                                
                                ''' record resource allocation '''
                                time.sleep(1)
                                for cluster in wrk_log_path_dict:
                                    record_pod_resource_allocation(wrk_log_path_dict[cluster], rps_dict[cluster])
                                    
                                ''' record resource usage 20 before the end of the experiment '''
                                sleep_before_resource_usage_recording = CONFIG['duration'] - 20
                                time.sleep(sleep_before_resource_usage_recording)
                                print(f"sleep for {sleep_before_resource_usage_recording} seconds before resource resource usage")
                                for cluster in wrk_log_path_dict:
                                    record_pod_resource_usage(wrk_log_path_dict[cluster], rps_dict[cluster])
                                    
                                ''' Join all threads '''
                                for future in concurrent.futures.as_completed(future_list):
                                    print(future.result())
                                    
                            print("Both wrk2 have completed.")
                            
                            if mode == "profile":
                                src_in_pod = "/app/trace_string.csv"
                                dst_in_host = f"{output_dir}/trace.slatelog"
                                kubectl_cp_from_slate_controller_to_host(src_in_pod, dst_in_host)
                            elif mode == "runtime":
                                if routing_rule == "WATERFALL" or routing_rule == "SLATE":
                                    file_list = ["constraint.csv", "variable.csv", "network_df.csv", "compute_df.csv", "gurobi_model.ilp"]
                                    for file in file_list:
                                        src_in_pod = f"/app/{file}"
                                        dst_in_host = file
                                        kubectl_cp_from_slate_controller_to_host(src_in_pod, dst_in_host)
                                        
                                src_in_pod = "/app/sim_percentage_df_most_recent.csv"
                                dst_in_host = f'{output_dir}/{src_in_pod.split("/")[-1]}'
                                kubectl_cp_from_slate_controller_to_host(src_in_pod, dst_in_host)
                                
                                src_in_pod = "/app/sim_percentage_df_history.csv"
                                dst_in_host = f'{output_dir}/{src_in_pod.split("/")[-1]}'
                                kubectl_cp_from_slate_controller_to_host(src_in_pod, dst_in_host)
                            else:
                                print("???")
                                print(f"mode: {mode} is not supported")
                                exit()
                            '''end of one set of experiment'''
                            restart_deploy(exclude=[])
                            
                            per_wrk_et = datetime.now()
                            per_wk_duration = (per_wrk_et - per_wrk_st).seconds
                            print(f"@@ per_wk_duration: {per_wk_duration} seconds")
                    end_time = datetime.now()
                    duration = (end_time - start_time).seconds
                    print(f"@@ Total runtime: {duration} seconds")
    run_command("bash ../delete_node_level_tc_qdisc.sh")
if __name__ == "__main__":
    main()