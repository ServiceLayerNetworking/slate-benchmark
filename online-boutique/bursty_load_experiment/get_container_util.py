from kubernetes import client, config
from apscheduler.schedulers.blocking import BlockingScheduler
import datetime
import csv

# Function to initialize or append to a CSV file
def setup_csv():
    try:
        with open('pod_cpu_memory_usage.csv', mode='x', newline='') as file:
            writer = csv.writer(file)
            writer.writerow([
                "Timestamp", "Pod Name", "Namespace", 
                "App CPU Usage (millicores)", "App Memory Usage (MiB)", 
                "Istio CPU Usage (millicores)", "Istio Memory Usage (MiB)"
            ])
    except FileExistsError:
        pass

def safe_convert_cpu_to_millicores(cpu_usage):
    try:
        # Assuming 'cpu_usage' ends with 'n' for nanocores
        return int(cpu_usage[:-1]) / 1_000_000
    except (ValueError, TypeError):
        return None

def safe_convert_memory_to_mib(memory_usage):
    try:
        # Assuming 'memory_usage' ends with 'Ki' for kibibytes
        return int(memory_usage[:-2]) / 1024
    except (ValueError, TypeError):
        return None

def get_cpu_memory_utilization():
    config.load_kube_config()
    api = client.CustomObjectsApi()
    try:
        resp = api.list_cluster_custom_object("metrics.k8s.io", "v1beta1", "pods")
        with open('pod_cpu_memory_usage.csv', mode='a', newline='') as file:
            writer = csv.writer(file)
            for pod_metrics in resp.get('items', []):
                pod_name = pod_metrics['metadata']['name']
                namespace = pod_metrics['metadata']['namespace']
                
                app_cpu_usage, app_memory_usage = None, None
                istio_cpu_usage, istio_memory_usage = None, None

                for container in pod_metrics['containers']:
                    container_name = container['name']
                    cpu_usage = container['usage']['cpu']
                    memory_usage = container['usage']['memory']
                    
                    if container_name == 'istio-proxy':
                        istio_cpu_usage = safe_convert_cpu_to_millicores(cpu_usage)
                        istio_memory_usage = safe_convert_memory_to_mib(memory_usage)
                    else:
                        app_cpu_usage = safe_convert_cpu_to_millicores(cpu_usage)
                        app_memory_usage = safe_convert_memory_to_mib(memory_usage)
                
                timestamp = datetime.datetime.now()
                writer.writerow([
                    timestamp, pod_name, namespace, 
                    app_cpu_usage, app_memory_usage, 
                    istio_cpu_usage, istio_memory_usage
                ])
    except client.rest.ApiException as e:
        print(f"Exception when calling Metrics API: {e}")

# Set up CSV file on script start
setup_csv()

# Create a scheduler that runs in the background
scheduler = BlockingScheduler()

# Schedule the get_cpu_memory_utilization to be called every second
scheduler.add_job(get_cpu_memory_utilization, 'interval', seconds=1)

print("Starting scheduler to record CPU and memory usage for app and istio containers...")

# Start the scheduler
scheduler.start()
