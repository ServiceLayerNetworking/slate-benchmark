import subprocess

def run_command(command):
    try:
        print(f"Executing: {command}")
        output = subprocess.check_output(command, stderr=subprocess.STDOUT, shell=True, universal_newlines=True)
        print("Success\n")
        return output
    except subprocess.CalledProcessError as e:
        print(f"Command failed: {e.output.strip()}")
        return None

def apply_latency(source_pod, destinations):
    # Clean existing configuration
    run_command(f"kubectl exec --stdin --tty {source_pod} -- tc qdisc del dev eth0 root")
    
    # Add root prio qdisc
    run_command(f"kubectl exec --stdin --tty {source_pod} -- tc qdisc add dev eth0 root handle 1: prio bands 3")
    
    handle_id = 10  # Start for class handles
    class_id = 1    # Start for class IDs

    for dst_ip in destinations:
        print(f"Applying 80ms delay to traffic from {source_pod} to {dst_ip}")

        # Create a class under the root qdisc
        class_handle = f"1:{class_id}"
        run_command(f"kubectl exec --stdin --tty {source_pod} -- tc class add dev eth0 parent 1: classid {class_handle} htb rate 1000Mbps")

        # Add netem qdisc to the class for delay
        netem_handle = f"{handle_id}:"  # Netem qdisc handle
        run_command(f"kubectl exec --stdin --tty {source_pod} -- tc qdisc add dev eth0 parent {class_handle} handle {netem_handle} netem delay 80ms")
        
        # Direct traffic to the class based on destination IP
        run_command(f"kubectl exec --stdin --tty {source_pod} -- tc filter add dev eth0 protocol ip parent 1: prio 1 u32 match ip dst {dst_ip} flowid {class_handle}")

        class_id += 1  # Increment for the next class
        handle_id += 10  # Increment for the next netem handle to ensure uniqueness

source_pod = "metrics-fake-ingress-us-west-1-f9f969d46-htjmx"
destination_ips = ["10.244.1.163", "10.244.1.164"]

apply_latency(source_pod, destination_ips)
