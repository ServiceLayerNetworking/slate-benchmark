import subprocess
import os

def run_command(command, check=True):
    print(f"Trying to run {command}")
    try:
        subprocess.run(command, check=check, shell=True)
        print(f"success")
    except subprocess.CalledProcessError as e:
        print(f"fail: {e.cmd}")
        print("exit...")
        assert False
        

def get_pods_by_label(label_selector):
    command = f"kubectl get pods --selector={label_selector} -o jsonpath='{{.items[*].metadata.name}}'"
    pod_names = subprocess.getoutput(command)
    return pod_names.split()

# Adds a new queuing discipline (qdisc) to an interface
def add_new_qdisc(src_pod):
    cmd = f"kubectl exec --stdin --tty {src_pod} -- tc qdisc add dev eth0 root handle 1: prio",
    run_command(cmd)

def tc_inject_latency(src_pod, dst_pod_ip_addr, latency=100):
    inject_latency_commands = [
        f"kubectl exec --stdin --tty {src_pod} -- tc filter add dev eth0 parent 1:0 protocol ip prio 1 u32 match ip dst {dst_pod_ip_addr} flowid 2:1",
        f"kubectl exec --stdin --tty {src_pod} -- tc qdisc add dev eth0 parent 1:1 handle 2: netem delay {latency}ms",
    ]
    for cmd in inject_latency_commands:
        run_command(cmd)

# Get names of all pods with "region: us-east-1" label
west_pods = get_pods_by_label("region=us-west-1")
east_pods = get_pods_by_label("region=us-east-1")

# print("Pods with 'region: us-west-1' label:")
# for wp in west_pods:
#     print(wp)
# print()
# print("Pods with 'region: us-east-1' label:")
# for ep in east_pods:
#     print(ep)


    # add_new_qdisc(src_pod)
    # tc_inject_latency(src_pod, dst_pod_ip_addr)
    # print(f"** adding qdisc rules in {src_pod} to {dst_pod} ({dst_pod_ip_addr})\n")

dst_pod_map = dict()
for dst_pod in east_pods:
    dst_pod_map[dst_pod] = subprocess.getoutput(f"kubectl get pod " + dst_pod + " -o=jsonpath='{.status.podIP}'")
    
for src_pod in west_pods:
    # run_command(f"kubectl exec --stdin --tty {src_pod} -- tc qdisc del dev eth0 root", check=False)
    
    latency = 50
    run_command(f"kubectl exec --stdin --tty {src_pod} -- tc qdisc add dev eth0 root handle 1: prio")
    
    for dst_pod, dst_ip in dst_pod_map.items():
        print("-"*50)
        print(f'** src_pod: {src_pod}, dst_pod: {dst_pod}, dst_ip: {dst_ip}')
        print("-"*50)
        print(f"Applying {latency}ms delay from {src_pod} to {dst_pod} (IP {dst_ip})")
        
        run_command(f"kubectl exec --stdin --tty {src_pod} -- tc filter add dev eth0 parent 1:0 protocol ip prio 1 u32 match ip dst {dst_ip} flowid 2:1")
        run_command(f"kubectl exec --stdin --tty {src_pod} -- tc qdisc add dev eth0 parent 1:1 handle 2: netem delay {latency}ms")
        print()
        
        # exit()
    print(f"DONE: {src_pod}")
    print("="*80)
    
    
###################