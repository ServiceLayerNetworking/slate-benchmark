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
                    line = lines[i].strip()
                    key = line.split(',')[0]
                    value = line.split(',')[1]
                    if key == "inter_cluster_latency":
                        '''NOTE: inter_cluster_latency config will not be used when plotting latency graph'''
                        src = line.split(',')[1]
                        dst = line.split(',')[2]
                        lat = line.split(',')[3]
                    
                except Exception as e:
                    print(f"Error: {e}")
                    print(lines[i])
                    exit()
                if key == "inter_cluster_latency":
                    print("skip inter_cluster_latency config")
                else:
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

def get_real_rps_tput():
    tput = r"Requests/sec:\s*(\d+\.\d+)" 
    return tput

def parse_latency_stat_in_wrklog_file(wrklog_path, wrk_config, latency_metrics, rps_thr, latency_dict):
    latency_patterns = regex_pattern(latency_metrics)
    with open(wrklog_path, 'r') as file:
        wrklog_file_read = file.read()
        
        #########################################
        pattern = r"Requests/sec:\s*(\d+\.\d+)"
        match = re.search(pattern, wrklog_file_read)
        if match:
            tput = float(match.group(1))
            print("Requests per second:", tput)
        else:
            print("Pattern not found")
            assert False
        #########################################
        
        cluster = wrk_config["cluster"]
        rps_value = int(wrk_config[f"{cluster}_RPS"])
        if rps_value <= rps_thr:
            for key, pattern in latency_patterns.items():
                latency_value = find_latency_value(pattern, wrklog_file_read)
                print(f"key: {key}, latency_value: {latency_value}")
                if key not in latency_dict:
                    latency_dict[key] = []
                latency_dict[key].append(latency_value)
            if "rps" not in latency_dict:
                latency_dict["mode"] = []
                latency_dict["cluster"] = []
                latency_dict["rps"] = []
                latency_dict["routing_rule"] = []
                latency_dict["tput"] = []
                # latency_dict["inter_cluster_latency"] = []
            latency_dict["rps"].append(rps_value)
            latency_dict["mode"].append(wrk_config["mode"])
            latency_dict["routing_rule"].append(wrk_config["routing_rule"])
            # latency_dict["inter_cluster_latency"].append(int(wrk_config["inter_cluster_latency"]))
            latency_dict["cluster"].append(wrk_config["cluster"])
            latency_dict["tput"].append(tput)
        
def find_and_process_wrklog_files(base_directory):
    wrklog_files = glob.glob(f'{base_directory}/**/*.wrklog', recursive=True)
    return wrklog_files


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python script.py <rps_threshold> <input_directory>")
        sys.exit(1)
    latency_metrics = ['avg', '50%'] #, '99%']
    rps_threshold = int(sys.argv[1])
    base_directory = sys.argv[2]
    wrklog_files = find_and_process_wrklog_files(base_directory)
    latency_dict = dict()
    for wrklog_path in wrklog_files:
        wrk_config = parse_wrk_config(wrklog_path)
        print(wrk_config)
        parse_latency_stat_in_wrklog_file(wrklog_path, wrk_config, latency_metrics, rps_threshold, latency_dict)
    print("latency_dict")
    for key, value in latency_dict.items():
        print(f"{key}: {value}")
    
    df = pd.DataFrame(latency_dict)
    for metric in latency_metrics:
        df[metric] = pd.to_numeric(df[metric], errors='coerce')
    df['rps'] = pd.to_numeric(df['rps'], errors='coerce').astype(int)
    df['tput'] = pd.to_numeric(df['tput'], errors='coerce').astype(int)
    df.sort_values(by='rps', inplace=True)
    plt.figure(figsize=(10, 6))
    for mode in df['mode'].unique():
        for routing_rule in df['routing_rule'].unique():
            # for inter_cluster_latency in df['inter_cluster_latency'].unique():
            for cluster in df['cluster'].unique():
                # df_filtered = df[(df['mode'] == mode) & (df['routing_rule'] == routing_rule) & (df['inter_cluster_latency'] == inter_cluster_latency) & (df['cluster'] == cluster)]
                df_filtered = df[(df['mode'] == mode) & (df['routing_rule'] == routing_rule) & (df['cluster'] == cluster)]
                df_filtered.to_csv("asdf.csv")
                for metric in latency_metrics:
                    plt.plot(df_filtered['rps'], df_filtered[metric], label=f"rps-{routing_rule}-{cluster}-{metric}", marker='o')
                    plt.plot(df_filtered['rps'], df_filtered['tput'], marker='x', linestyle='--', alpha=0.5)
    
    
    plt.title(f'Latency', fontsize=20)
    plt.xlabel('Requests per Second (RPS)', fontsize=20)
    plt.ylabel('Latency (ms)', fontsize=20)
    plt.xticks(fontsize=14)  # Set x-tick label fontsize
    plt.yticks(fontsize=14)  # Set y-tick label fontsize
    plt.legend(fontsize=14)
    plt.grid(True)
    # plt.ylim((0,1000))
    svc_name = base_directory.split('/')[0]
    merged_string = ''.join(latency_metrics)
    pdf_file_path = f'{base_directory}/latency-{merged_string}.pdf'
    plt.savefig(pdf_file_path)
    plt.show()
    print(f"output pdf: {pdf_file_path}")
    # df.to_csv(f'latency.csv', index=False)
