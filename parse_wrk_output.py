import re
import sys
import glob
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

latency_dict = dict()
req_type = ""

def parse_wrk_config(log_content):
    config_patterns = {
        'distribution': r"distribution:\s+(\w+)",
        'duration': r"duration:\s+(\d+)",
        'req_type': r"req_type:\s+(\w+)",
        'RPS': r"RPS:\s+(\d+)",
        'cluster': r"cluster:\s+(\d+)",
    }

    wrk_config = {}
    for key, pattern in config_patterns.items():
        match = re.search(pattern, log_content)
        if match:
            wrk_config[key] = match.group(1)
        else:
            wrk_config[key] = "Value not found"
    return wrk_config

def find_latency_value(pattern, log_content):
    match = re.search(pattern, log_content)
    if match:
        value, unit = match.groups()
        # Convert value to milliseconds if in seconds
        if unit == 's':
            return str(float(value) * 1000)  # Convert to milliseconds
        return value  # Already in milliseconds
    else:
        return "Value not found"
    
def parse_experiment_config(filename):
    config = {}  # Dictionary to store configuration data
    with open(filename, 'r') as file:  # Open the file
        for line in file:  # Read each line in the file
            if line.find("@@") > -1:  # Check for the end marker
                print(f"End of config section, {line}")
                break  # Stop reading the file
            line = line.strip()
            key, value = line.strip().split(',', 1)  # Split each line into key and value
            config[key] = value  # Store the key-value pair in the dictionary
    return config


def parse_log_file(file_path, columns, rps_thr):
    experiment_config = parse_experiment_config(file_path)
    # print(f"config: {experiment_config}")
    
    # Include unit in the regex to differentiate between ms and s
    latency_patterns = dict()
    # columns = ['avg', '50%', '99%', '99.9%', '99.99%']
    for col in columns:
        if col == 'avg':
            latency_patterns[col] = r"Latency\s+(\d+\.\d+)(ms|s)"
        elif col == '50%':
            latency_patterns[col] = r"50\.000%\s+(\d+\.\d+)(ms|s)"
        elif col == '99%':
            latency_patterns[col] = r"99\.000%\s+(\d+\.\d+)(ms|s)"
        elif col == '99.9%':
            latency_patterns[col] = r"99\.900%\s+(\d+\.\d+)(ms|s)"  
        elif col == '99.99%':
            latency_patterns[col] = r"99\.990%\s+(\d+\.\d+)(ms|s)"
        else:
            print(f"Unknown column: {col}")
            sys.exit(1)
    #  latency_patterns = {
    #     'avg': r"Latency\s+(\d+\.\d+)(ms|s)",
    #     '50%': ,
    #     '99%': r"99\.000%\s+(\d+\.\d+)(ms|s)",
    #     # '99.9%': r"99\.900%\s+(\d+\.\d+)(ms|s)",
    #     # '99.99%': r"99\.990%\s+(\d+\.\d+)(ms|s)"
    # }

    try:
        with open(file_path, 'r') as file:
            log_content = file.read()
    except Exception as e:
        print(f"Error opening file {file_path}: {e}")
        return
    
    
    '''
    latency_dict['avg'] = [1, 2, 3, 4, 5]
    latency_dict['99%'] = [10, 20, 30, 40, 50]
    latency_dict['rps'] = [100, 200, 300, 400, 500]
    
    experiment_config['mode'] = 'runtime'
    experiment_config['routing_rule'] = 'LOCAL'
    experiment_config['RPS'] = '100'
    experiment_config['inter_cluster_latency'] = '0'
    experiment_config['total_num_services'] = '3'
    experiment_config['benchmark_name'] = 'metrics'
    '''
    wrk_config = parse_wrk_config(log_content)
    rps_value = int(wrk_config.get("RPS", 0))
    if rps_value <= rps_thr:
        for key, pattern in latency_patterns.items():
            latency_value = find_latency_value(pattern, log_content)
            # print(f"key: {key}, latency_value: {latency_value}")
            if key not in latency_dict:
                latency_dict[key] = []
            latency_dict[key].append(latency_value)

        global req_type
        req_type = wrk_config.get("req_type", "unknown")

        if "rps" not in latency_dict:
            latency_dict["rps"] = []
            latency_dict["mode"] = []
            latency_dict["routing_rule"] = []
            latency_dict["inter_cluster_latency"] = []
            latency_dict["cluster"] = []
            
        latency_dict["rps"].append(rps_value)
        latency_dict["mode"].append(experiment_config["mode"])
        latency_dict["routing_rule"].append(experiment_config["routing_rule"])
        latency_dict["inter_cluster_latency"].append(int(experiment_config["inter_cluster_latency"]))
        latency_dict["cluster"].append(wrk_config["cluster"])
        

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python script.py <rps_threshold> <input_files> ")
        sys.exit(1)

    rps_threshold = int(sys.argv[1])
    output_file = sys.argv[2]
    print(f"NOTE: rps_threshold: {rps_threshold}")
    # columns = ['avg', '50%', '99%', '99.9%', '99.99%']
    columns = ['avg', '50%', '99%']
    # columns = ['avg']
    # columns = ['avg', '50%']
    for pattern in sys.argv[2:]:
        for file_path in glob.glob(pattern):
            parse_log_file(file_path, columns, rps_threshold)


    df = pd.DataFrame(latency_dict)
    
    # Convert all latency values to numeric, assuming non-numeric values are errors or 'Value not found'
    for col in columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    # Ensure 'rps' column is integer
    df['rps'] = pd.to_numeric(df['rps'], errors='coerce').astype(int)

    df.sort_values(by='rps', inplace=True)
    
    plt.figure(figsize=(10, 6))
    for mode in df['mode'].unique():
        for rule in df['routing_rule'].unique():
            for inter_cluster_latency in df['inter_cluster_latency'].unique():
                for cluster in df['cluster'].unique():
                    if inter_cluster_latency == 20:
                        df_filtered = df[(df['mode'] == mode) & (df['routing_rule'] == rule) & (df['inter_cluster_latency'] == inter_cluster_latency) & (df['cluster'] == cluster)]
                        plt.plot(df_filtered['rps'], df_filtered['avg'], label=f"{mode}-{rule}-{inter_cluster_latency}-{cluster}", marker='o')
                
    # for column in columns:
    #     plt.plot(df['rps'], df[column], label=column, marker='o')

    plt.title(f'{req_type}', fontsize=20)
    plt.xlabel('Requests per Second (RPS)', fontsize=20)
    plt.ylabel('Latency (ms)', fontsize=20)
    plt.xticks(fontsize=14)  # Set x-tick label fontsize
    plt.yticks(fontsize=14)  # Set y-tick label fontsize
    plt.legend(fontsize=14)
    # plt.ylim((0,1000))
    plt.savefig(f'latency-{req_type}-{output_file}.png')
    plt.show()

    df.to_csv(f'latency_{req_type}.csv', index=False)