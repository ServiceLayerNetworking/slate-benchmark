import subprocess

def run_command(command):
    try:
        subprocess.run(command, check=True, shell=True)
    except subprocess.CalledProcessError as e:
        print(f"An error occurred: {e}")
        print(f"Command: {e.cmd}")
        print("exit...")
        exit()
        

def get_pods_by_label(label_selector):
    command = f"kubectl get pods --selector={label_selector} -o jsonpath='{{.items[*].metadata.name}}'"
    pod_names = subprocess.getoutput(command)
    return pod_names.split()

# Get names of all pods with "region: us-east-1" label
west_pods = get_pods_by_label("region=us-west-1")
east_pods = get_pods_by_label("region=us-east-1")

print("Pods with 'region: us-west-1' label:")
for wp in west_pods:
    print(wp)
print()
print("Pods with 'region: us-east-1' label:")
for ep in east_pods:
    print(ep)

for src_pod in west_pods:
    # run_command(f"kubectl exec --stdin --tty {src_pod} -- tc qdisc del dev eth0 root")
    print(f"source pod: {src_pod}")
    for dst_pod in east_pods:
        src_app = subprocess.getoutput("kubectl get pod " + src_pod + " -o=jsonpath='{.metadata.labels.app}'")
        dst_app = subprocess.getoutput("kubectl get pod " + dst_pod + " -o=jsonpath='{.metadata.labels.app}'")
        # if src_app == dst_app:
        #     # No need to inject network latency between west-frontend and east-frontend
        #     continue
        
        dst_pod_ip_addr = subprocess.getoutput(cmd)
        # Get destination IP addresses
        cmd = "kubectl get pod " + dst_pod + " -o=jsonpath='{.status.podIP}'"
        dst_pod_ip_addr = subprocess.getoutput(cmd)
        print(f"dst pod: {dst_pod}, ip: {dst_pod_ip_addr}")
        
        # Delete all existing qdisc rules
        cmd = "kubectl exec --stdin --tty deploy/b-v1 -- tc qdisc del dev eth0 root"
        run_command(cmd)
        print(cmd)

        # Add qdisc rules with delay
        commands = [
            f"kubectl exec --stdin --tty {src_pod} -- tc qdisc add dev eth0 root handle 1: prio",
            f"kubectl exec --stdin --tty {src_pod} -- tc filter add dev eth0 parent 1:0 protocol ip prio 1 u32 match ip dst {dst_pod} flowid 2:1",
            f"kubectl exec --stdin --tty {src_pod} -- tc qdisc add dev eth0 parent 1:1 handle 2: netem delay 50ms",
        ]

        for cmd in commands:
            run_command(cmd)
            print(cmd)
            
        print(f"** Finish adding qdisc rules in {src_pod} to {dst_pod}")
        exit()