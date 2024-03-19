import re
import sys
import glob
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import subprocess

def parse_wrk_config(wrklog_path):
    wrk_config = dict()
    lines = open(wrklog_path, 'r').readlines()
    i = 0
    while i < len(lines):
        if lines[i].strip() == "-- start of config --":
            i += 1
            while True:
                if lines[i].strip() == "-- end of config --":
                    break
                try:
                    key = lines[i].strip().split(',')[0]
                    value = lines[i].strip().split(',')[1]
                except Exception as e:
                    print(f"Error: {e}")
                    print(lines[i])
                    exit()
                wrk_config[key] = value
                i += 1
        i += 1
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

def regex_pattern(latency_metrics):
    latency_patterns = dict()
    for metric in latency_metrics:
        if metric == 'avg':
            latency_patterns[metric] = r"Latency\s+(\d+\.\d+)(ms|s)"
        elif metric == '50%':
            latency_patterns[metric] = r"50\.000%\s+(\d+\.\d+)(ms|s)"
        elif metric == '99%':
            latency_patterns[metric] = r"99\.000%\s+(\d+\.\d+)(ms|s)"
        elif metric == '99.9%':
            latency_patterns[metric] = r"99\.900%\s+(\d+\.\d+)(ms|s)"  
        elif metric == '99.99%':
            latency_patterns[metric] = r"99\.990%\s+(\d+\.\d+)(ms|s)"
        else:
            print(f"Unknown metric: {metric}")
            sys.exit(1)
    return latency_patterns


def parse_latency_stat_in_wrklog_file(wrklog_path, experiment_config, latency_metrics, rps_thr, latency_dict):
    latency_patterns = regex_pattern(latency_metrics)
    with open(wrklog_path, 'r') as file:
        log_content = file.read()
        cluster = experiment_config["cluster"]
        rps_value = int(experiment_config[f"{cluster}_RPS"])
        if rps_value <= rps_thr:
            for key, pattern in latency_patterns.items():
                latency_value = find_latency_value(pattern, log_content)
                print(f"key: {key}, latency_value: {latency_value}")
                if key not in latency_dict:
                    latency_dict[key] = []
                latency_dict[key].append(latency_value)
            if "rps" not in latency_dict:
                latency_dict["mode"] = []
                latency_dict["cluster"] = []
                latency_dict["rps"] = []
                latency_dict["routing_rule"] = []
                latency_dict["inter_cluster_latency"] = []
            latency_dict["rps"].append(rps_value)
            latency_dict["mode"].append(experiment_config["mode"])
            latency_dict["routing_rule"].append(experiment_config["routing_rule"])
            latency_dict["inter_cluster_latency"].append(int(experiment_config["inter_cluster_latency"]))
            latency_dict["cluster"].append(experiment_config["cluster"])
        
def find_and_process_wrklog_files(base_directory):
    wrklog_files = glob.glob(f'{base_directory}/**/*.wrklog', recursive=True)
    return wrklog_files


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python script.py <rps_threshold> <input_directory>")
        sys.exit(1)
    latency_metrics = ['avg', '50%']
    # latency_metrics = ['avg', '50%']
    # latency_metrics = ['avg', '50%']
    rps_threshold = int(sys.argv[1])
    base_directory = sys.argv[2]
    wrklog_files = find_and_process_wrklog_files(base_directory)
    latency_dict = dict()
    for wrklog_path in wrklog_files:
        wrk_config = parse_wrk_config(wrklog_path)
        parse_latency_stat_in_wrklog_file(wrklog_path, wrk_config, latency_metrics, rps_threshold, latency_dict)
    print("latency_dict")
    for key, value in latency_dict.items():
        print(f"{key}: {value}")
    
    df = pd.DataFrame(latency_dict)
    for metric in latency_metrics:
        df[metric] = pd.to_numeric(df[metric], errors='coerce')
    df['rps'] = pd.to_numeric(df['rps'], errors='coerce').astype(int)
    df.sort_values(by='rps', inplace=True)
    plt.figure(figsize=(10, 6))
    for mode in df['mode'].unique():
        for routing_rule in df['routing_rule'].unique():
            for inter_cluster_latency in df['inter_cluster_latency'].unique():
                for cluster in df['cluster'].unique():
                    df_filtered = df[(df['mode'] == mode) & (df['routing_rule'] == routing_rule) & (df['inter_cluster_latency'] == inter_cluster_latency) & (df['cluster'] == cluster)]
                    for metric in latency_metrics:
                        plt.plot(df_filtered['rps'], df_filtered[metric], label=f"{routing_rule}-{inter_cluster_latency}-{cluster}-{metric}", marker='o')
                
    plt.title(f'Latency', fontsize=20)
    plt.xlabel('Requests per Second (RPS)', fontsize=20)
    plt.ylabel('Latency (ms)', fontsize=20)
    plt.xticks(fontsize=14)  # Set x-tick label fontsize
    plt.yticks(fontsize=14)  # Set y-tick label fontsize
    plt.legend(fontsize=14)
    # plt.ylim((0,1000))
    svc_name = base_directory.split('/')[0]
    merged_string = ''.join(latency_metrics)
    pdf_file_path = f'{base_directory}/latency-{merged_string}.pdf'
    plt.savefig(pdf_file_path)
    plt.show()
    print(f"output pdf: {pdf_file_path}")
    # df.to_csv(f'latency.csv', index=False)