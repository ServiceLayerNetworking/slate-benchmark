import subprocess

def run_command(command, check=True):
    try:
        subprocess.run(command, check=check, shell=True)
        print(f"success: {command}")
    except subprocess.CalledProcessError as e:
        print(f"An error occurred: {e}")
        print(f"Command: {e.cmd}")
        print("exit...")
        exit()

def get_all_pods():
    cmd = "kubectl get pods -n default -o=jsonpath='{.items[*].metadata.name}'"
    pod_names = subprocess.getoutput(cmd)
    return pod_names.split()

# Get names of all pods with "region: us-east-1" label
all_pods = get_all_pods()
# print(all_pods)

for pod in all_pods:
    print(f"pod: {pod}")
    # Delete all existing qdisc rules in the src pod
    delete_qdisc_cmd = f"kubectl exec --stdin --tty {pod} -- tc qdisc del dev eth0 root"
    run_command(delete_qdisc_cmd, check=False)