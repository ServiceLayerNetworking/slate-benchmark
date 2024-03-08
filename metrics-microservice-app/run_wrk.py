import os
import subprocess
from datetime import datetime
from kubernetes import client, config
import math
import time
import concurrent.futures
import sys
import os

sys.path.append('/users/gangmuk/projects/SLATE/global-controller')
import config as cfg

# Config
CONFIG = {
    'distribution': 'exp',
    'thread': 50,
    'connection': 50,
    'duration': 30
}



def update_env(mode, benchmark_name, total_num_services, routing_rule, RPS, latency):
    print("update_env")
    temp=""
    temp+=f"mode,{mode}\n"
    temp+=f"routing_rule,{routing_rule}\n"
    temp+=f"RPS,{RPS}\n"
    temp+=f"inter_cluster_latency,{latency}\n"
    temp+=f"benchmark_name,{benchmark_name}\n"
    temp+=f"total_num_services,{total_num_services}\n"
    print(f"env: {temp}")
    
    # File to update
    file_path = "env.txt"
    with open(file_path, "w") as file:
        file.write(f"{temp}")
        
    # Get the pod name
    try:
        result = subprocess.run(["kubectl", "get", "pods", "-l", "app=slate-controller", "-o", "custom-columns=:metadata.name"], capture_output=True, text=True, check=True)
        slate_controller_pod = result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error fetching the slate-controller pod: {e}")
        sys.exit()

    # Copy the file to the pod
    try:
        subprocess.run(["kubectl", "cp", file_path, f"{slate_controller_pod}:/app/env.txt"], check=True)
        print(f"kubectl cp {file_path} {slate_controller_pod}:/app/env.txt")
    except subprocess.CalledProcessError as e:
        print(f"Error copying {file_path} to the pod: {e}")
        sys.exit()

    # Optionally, print the contents of the file
    # try:
    #     with open(file_path, "r") as file:
    #         print(file.read())
    # except IOError as e:
    #     print(f"Error reading file {file_path} after modification: {e}")
    #     sys.exit()
        
'''
slate_controller/env.txt => local file
'''
def scp_env_txt(output_path):
    print(f"scp_env_txt")
    slate_controller_pod = run_command("kubectl get pods -l app=slate-controller -o custom-columns=:metadata.name")
    src_path = "/app/env.txt"
    temp_file = "temp_env.txt"
    run_command(f"kubectl cp {slate_controller_pod}:{src_path} {temp_file}")
    run_command(f"cat {temp_file} > {output_path}.wrklog")
    # run_command(f"rm {temp_file}")
    print(f"src_env_file: {slate_controller_pod}:{src_path}")
    print(f"update {output_path} with env.txt")

def scrape_resource_config():
    # Load Kubernetes configuration from default location or a specific kubeconfig file
    config.load_kube_config()

    # Create a Kubernetes API client
    api_instance = client.AppsV1Api()

    try:
        namespace = "default"
        deployments = api_instance.list_namespaced_deployment(namespace, watch=False)
        resource_allocation = ""
        for deployment in deployments.items:
            metadata = deployment.metadata
            spec = deployment.spec.template.spec.containers[0]

            cpu_limit = spec.resources.limits.get("cpu") if spec.resources.limits else "N/A"
            cpu_request = spec.resources.requests.get("cpu") if spec.resources.requests else "N/A"
            mem_limit = spec.resources.limits.get("mem") if spec.resources.limits else "N/A"
            mem_request = spec.resources.requests.get("mem") if spec.resources.requests else "N/A"

            resource_allocation += f"Deployment,{metadata.name}\n"
            resource_allocation += f"CPU Limit,{cpu_limit}\n"
            resource_allocation += f"CPU Request,{cpu_request}\n"
            resource_allocation += f"Mem Limit,{mem_limit}\n"
            resource_allocation += f"Mem Request,{mem_request}\n"

    except Exception as e:
        print(f"Error: {e}")
        
    return resource_allocation

def convert_memory_to_mib(memory_usage):
    # Convert memory usage to MiB
    unit = memory_usage[-2:]  # Extract the unit (Ki, Mi, Gi)
    value = int(memory_usage[:-2])  # Extract the numeric value
    if unit == "Ki":
        return value / 1024  # 1 MiB = 1024 KiB
    elif unit == "Mi":
        return value
    elif unit == "Gi":
        return value * 1024  # 1 GiB = 1024 MiB
    else:
        return value / (1024**2)  # Assume the value is in bytes if no unit

def convert_cpu_to_millicores(cpu_usage):
    # Convert CPU usage to millicores
    if cpu_usage.endswith('n'):  # nanocores
        return int(cpu_usage.rstrip('n')) / 1000000
    elif cpu_usage.endswith('u'):  # assuming 'u' to be a unit close to millicores
        return int(cpu_usage.rstrip('u')) / 1000  # Convert assuming 'u' represents microcores
    else:
        return int(cpu_usage)  # Assuming direct millicore value


def get_pod_resource_metrics(namespace='default'):
    # Load the kubeconfig file
    config.load_kube_config()

    # Create a client for the Metrics API
    api = client.CustomObjectsApi()

    # Fetch the pod metrics in the specified namespace
    try:
        metrics = api.list_namespaced_custom_object(
            group="metrics.k8s.io",
            version="v1beta1",
            namespace=namespace,
            plural="pods"
        )
        output_str = ""
        for pod in metrics['items']:
            # print(f"Pod: {pod['metadata']['name']}")
            output_str += f"Pod: {pod['metadata']['name']}\n"
            for container in pod['containers']:
                container_name = container['name']
                cpu_usage = pod['containers'][0]['usage']['cpu']
                cpu_usage_millicores = convert_cpu_to_millicores(cpu_usage)
                memory_usage = container['usage']['memory']
                # Convert memory usage to MiB
                memory_usage_mib = convert_memory_to_mib(memory_usage)
                # print(f"Container: {container_name}, CPU: {math.ceil(cpu_usage_millicores)}m, Memory: {math.ceil(memory_usage_mib)} MiB")
                output_str += f"Container: {container_name}, CPU: {math.ceil(cpu_usage_millicores)}m, Memory: {math.ceil(memory_usage_mib)} MiB\n"

    except client.rest.ApiException as e:
        print(f"Exception when calling CustomObjectsApi->list_namespaced_custom_object: {e}")
    return output_str

def run_command(command):
    """Run shell command and return its output"""
    try:
        output = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT)
        return output.decode('utf-8').strip()
    except subprocess.CalledProcessError as e:
        print(f"Error executing command: {e.output.decode('utf-8')}")
        exit(1)
    

def run_wrk(cluster, req_type, rps, output_path, wasm_config, istio_config):
    nodename = run_command("kubectl get nodes | grep 'node1' | awk '{print $1}'")
    ingressgw_http2_nodeport = run_command("kubectl get svc istio-ingressgateway -n istio-system -o=json | jq '.spec.ports[] | select(.name==\"http2\") | .nodePort'")
    server_ip = f"http://{nodename}:{ingressgw_http2_nodeport}"
    print(server_ip)
    # name = f"{cluster}_{req_type}_{rps}.wrklog"
    # output_fn = os.path.join(dir, name)
    if rps < CONFIG["connection"]:
        CONFIG["connection"] = rps
    if CONFIG["connection"] < CONFIG["thread"]:
        CONFIG["thread"] = CONFIG["connection"]
    
    print(f'@@ Start {req_type} {rps}RPS to {cluster} for {CONFIG["duration"]} seconds (output_path: {output_path})')
    with open(output_path, "a") as f:
        f.write("@@ +++++++++++++++++++++++++++++++++++++++++++++++++ \n")
        info = f"""
--------------------------------
distribution: {CONFIG["distribution"]}
thread: {CONFIG["thread"]}
connection: {CONFIG["connection"]}
duration: {CONFIG["duration"]}
cluster: {cluster}
req_type: {req_type}
RPS: {rps}
WASM: {wasm_config}
ISTIO: {istio_config}
--------------------------------
"""
        f.write(info)

    wrk_command = f'./wrk -D {CONFIG["distribution"]} -t{CONFIG["thread"]} -c{CONFIG["connection"]} -d{CONFIG["duration"]} -L -S -s ./{cluster}_{req_type}.lua {server_ip} -R{rps} >> {output_path}'
    run_command(wrk_command)
    
    # It should be done ideally in the middle of the experiment not in the end
    with open(output_path, "a") as f:
        # current cpu and memory usage
        pod_metrics = get_pod_resource_metrics('default')
        f.write("@@ pod_metrics\n")
        f.write(pod_metrics)
        
        # current resource allocation (limit and request)
        resource_allocation = scrape_resource_config()
        f.write("@@ resource_allocation\n")
        f.write(resource_allocation)
    print("-"*50)
    print(f"{output_path}")
    print("-"*50)
    return

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

def restart_deploy(exclude=[]):
    def are_all_pods_ready(namespace='default'):
        # # Load kubeconfig
        # config.load_kube_config()

        # # Create a client for the CoreV1API
        # v1 = client.CoreV1Api()

        # # List all pods in the specified namespace
        # pods = v1.list_namespaced_pod(namespace)

        # # Check if all pods are ready
        # for pod in pods.items:
        #     if pod.status.conditions is None:
        #         return False
        #     for condition in pod.status.conditions:
        #         if condition.type != 'Ready' or condition.status != 'True' or pod.status.phase != 'Running' or condition.status == 'None' or pod.metadata.deletion_timestamp is not None:
        #             print(f"Pod {pod.metadata.name} is not ready")
        #             return False
        # return True
        # Load kubeconfig
        config.load_kube_config()

        # Create a client for the CoreV1API
        v1 = client.CoreV1Api()

        # List all pods in the specified namespace
        pods = v1.list_namespaced_pod(namespace)

        # Check if all pods are ready and no pods are in the process of terminating
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
    time.sleep(10)
    print("restart deploy is done")

def restart_slate_controller():
    run_command("kubectl rollout restart deploy slate-controller")
    print("@@ kubectl rollout restart deploy slate-controller")
    sleep_and_print(10)

def scp_trace_string_file(output_path, cluster, req_type, rps):
    print(f"scp_trace_string_file")
    slate_controller_pod = run_command("kubectl get pods -l app=slate-controller -o custom-columns=:metadata.name")
    src_path = "/app/trace_string.csv"
    run_command(f"kubectl cp {slate_controller_pod}:{src_path} {output_path}")
    print(f"src_path: {slate_controller_pod}:{src_path}")
    print("-"*50)
    print(f"{output_path}")
    print("-"*50)

def main():
    start_time = datetime.now()
    cluster = "west"
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
    total_num_services=3
    mode_and_routing_rule = {\
        # "profile": ["LOCAL"],\
        "runtime": ["REMOTE", "LOCAL", "SLATE", "MCLB"],\
        # "runtime": ["SLATE", "REMOTE"],\
        # "runtime": ["MCLB", "LOCAL", "SLATE", "REMOTE"],\
    }
    # oneway_latency = [0]
    oneway_latency = [0, cfg.INTER_CLUSTER_NETWORK_LATENCY]
    req_type_list = ["get_metric"] # It should match wrk2 lua script
    rps_list = {
                # "get_metric": [200], \
                "get_metric": [50, 100, 300, 400, 500], \
                # "get_metric": [50, 100, 150, 200, 250, 300, 350, 400, 450, 500], \
    }
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
            for mode in mode_and_routing_rule:
                for routing_rule in mode_and_routing_rule[mode]:
                    postfix = "Mar7th_morning"
                    print(f"* postfix for output file: {postfix}")
                    for req_type in req_type_list:
                        if istio_config:
                            if wasm_config:
                                output_dir = f"{req_type}-ww-{postfix}"
                            else:
                                output_dir = f"{req_type}-wow-{postfix}"
                        else:
                            output_dir = f"{req_type}-woi-{postfix}"
                        for RPS in rps_list[req_type]:
                            print(f"* mode: {mode}, routing_rule: {routing_rule}")
                            output_fn = f"{mode}-L{lat}-{routing_rule}-R{RPS}"
                            output_path = output_dir + f"/{output_fn}"
                            per_wrk_st = datetime.now()
                            
                            assert output_dir != ""
                            if not os.path.isdir(output_dir):
                                os.makedirs(output_dir)
                            
                            update_env(mode, benchmark_name, total_num_services, routing_rule, RPS, lat)
                            time.sleep(1)
                            
                            scp_env_txt(output_path)
                            time.sleep(1)
                            
                            run_wrk(cluster, req_type, RPS, output_path+".wrklog", wasm_config, istio_config)
                            scp_trace_string_file(output_path+".slatelog", cluster, req_type, RPS)
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