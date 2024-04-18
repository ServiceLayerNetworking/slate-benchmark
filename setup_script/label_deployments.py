import subprocess
import re

def get_deployments():
    # Get the list of deployments
    cmd = ["kubectl", "get", "deploy", "--no-headers", "-o", "custom-columns=NAME:.metadata.name"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception("Failed to get deployments: " + result.stderr)
    return result.stdout.strip().split()

def label_deployments(deployments):
    for deploy in deployments:
        # Regex to extract the region from the deployment name
        match = re.search(r'us-(central|east|south|west)-1', deploy)
        if match:
            region = match.group()
            label = f"region={region}"
            # Construct and execute the kubectl label command
            cmd = ["kubectl", "label", "deploy", deploy, label, "--overwrite"]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                print(f"Deployment {deploy} labeled with {label}")
            else:
                print(f"Failed to label {deploy}: {result.stderr}")

def main():
    try:
        deployments = get_deployments()
        label_deployments(deployments)
    except Exception as e:
        print(str(e))

if __name__ == "__main__":
    main()
