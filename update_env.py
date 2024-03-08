import argparse
import subprocess
import sys

def update_env(mode, benchmark_name, total_num_services, routing_rule):
    # Update the file based on provided arguments
    temp=""
    temp+=f"mode,{mode}\n"
    temp+=f"benchmark_name,{benchmark_name}\n"
    temp+=f"total_num_services,{total_num_services}\n"
    temp+=f"routing_rule,{routing_rule}\n"
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
    try:
        with open(file_path, "r") as file:
            print(file.read())
    except IOError as e:
        print(f"Error reading file {file_path} after modification: {e}")
        sys.exit()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Set environment configurations for the slate-controller.")
    parser.add_argument("--mode", choices=["profile", "runtime"], default="profile", required=True, help="The mode to set (either 'profile' or 'runtime').")
    parser.add_argument("--benchmark_name", choices=["metrics", "matmul", "hotelreservation"], help="Name of the benchmark.")
    parser.add_argument("--total_num_services", type=int, required=True, help="Total number of services.")
    parser.add_argument("--routing_rule", choices=["LOCAL", "REMOTE", "MCLB", "SLATE"], required=True, help="Routing rule to apply.")
    args = parser.parse_args()
    update_env(args.mode, args.benchmark_name, args.total_num_services, args.routing_rule)
