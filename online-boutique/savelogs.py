import os
import subprocess



def savelogs(parentdir, services=[]):
    # Directory to store the logs

    logs_directory = f"{parentdir}/proxy-logs"

    # Create the directory if it doesn't exist
    if not os.path.exists(logs_directory):
        os.makedirs(logs_directory)

    # Get the list of all pods in the default namespace
    try:
        pod_list_output = subprocess.check_output(['kubectl', 'get', 'pods', '-n', 'default', '-o', 'jsonpath={.items[*].metadata.name}'])
        pod_list = pod_list_output.decode('utf-8').split()
        
        # Loop through each pod
        for pod_name in pod_list:
            # if pod_name STARTS WITH any of the services, then save the logs
            if not any(pod_name.startswith(service) for service in services):
                continue
            # Retrieve logs of the istio-proxy container from the pod
            try:
                log_output = subprocess.check_output(['kubectl', 'logs', pod_name, '-c', 'istio-proxy', '-n', 'default'])
                
                # Save the logs to a file in the proxy-logs directory
                with open(f"{logs_directory}/{pod_name}.txt", "w") as log_file:
                    log_file.write(log_output.decode('utf-8'))
                print(f"Logs for {pod_name} saved successfully.")
            
            except subprocess.CalledProcessError as e:
                print(f"Error retrieving logs for {pod_name}: {e}")
                
    except subprocess.CalledProcessError as e:
        print(f"Error fetching pod list: {e}")

if __name__ == "__main__":
    parentdir = "foobar2"
    savelogs(parentdir, services=["sslateingress"])