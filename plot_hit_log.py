import re
import sys
import glob
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import subprocess
import json


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
        

def extract_cdf_data(wrklog_path):
    with open(wrklog_path, 'r') as file:
        # Flag to indicate if we are in the "Detailed Percentile spectrum" section
        in_cdf_section = False
        cdf_data = []
        for line in file:
            if "Detailed Percentile spectrum:" in line:
                in_cdf_section = True
                continue
            if in_cdf_section:
                if "----" in line:
                    break  # End of the CDF section
                # Extract the relevant data using regular expression
                match = re.match(r"\s*(\d+\.\d+)\s+(\d+\.\d+)", line)
                if match:
                    value, percentile = match.groups()
                    cdf_data.append((float(value), float(percentile)))
    return cdf_data


def find_and_process_wrklog_files(base_directory):
    wrklog_files = glob.glob(f'{base_directory}/**/*.wrklog', recursive=True)
    for file in wrklog_files:
        print(file)
    return wrklog_files


def parse_latencies_from_hit_log(file_path):
    latencies_ns = []
    with open(file_path, 'r') as file:
        # Skip lines until the specific starting line is found
        while True:
            line = file.readline()
            if "Running test for" in line:
                break  # Found the starting line, stop skipping
            if not line:
                return latencies_ns  # Reached end of file without finding the starting line

        for line in file:
            try:
                # Parse each line as a JSON object
                log_entry = json.loads(line)
                # Extract the 'LatencyNs' field
                latencies_ns.append(log_entry['LatencyNs'])
            except json.JSONDecodeError:
                print("Error decoding JSON from line:", line)
            except KeyError:
                print("Key 'LatencyNs' not found in line:", line)
    latencies_ms = [elem / 1e6 for elem in latencies_ns]
    latencies_ms_sorted = np.sort(latencies_ms)
    cdf = np.arange(1, len(latencies_ms_sorted) + 1) / len(latencies_ms_sorted)
    return latencies_ms_sorted, cdf


def parse_latency_stat_in_wrklog_file(wrklog_path, wrk_config):
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
            latency_dict["rps"].append(rps_value)
            latency_dict["mode"].append(wrk_config["mode"])
            latency_dict["routing_rule"].append(wrk_config["routing_rule"])
            latency_dict["cluster"].append(wrk_config["cluster"])
            latency_dict["tput"].append(tput)
            
            if wrk_config["routing_rule"] not in stat_dict:
                stat_dict[wrk_config["routing_rule"]] = dict()
            if str(rps_value) not in stat_dict[wrk_config["routing_rule"]]:
                stat_dict[wrk_config["routing_rule"]][str(rps_value)] = dict()
            if wrk_config["cluster"] not in stat_dict[wrk_config["routing_rule"]][str(rps_value)]:
                stat_dict[wrk_config["routing_rule"]][str(rps_value)][wrk_config["cluster"]] = dict()
                
        
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python script.py <base_directory> ")
        sys.exit(1)
    wrk_config_list = list()
    base_directory = sys.argv[1]
    wrklog_files = find_and_process_wrklog_files(base_directory)
    for wrklog_path in wrklog_files:
        wrk_config = parse_wrk_config(wrklog_path)
        wrk_config["latencies_ms_sorted"], wrk_config["cdf"] = parse_latencies_from_hit_log(wrklog_path)
        # parse_latency_stat_in_wrklog_file(wrklog_path, wrk_config)
        wrk_config_list.append(wrk_config)
    
    for wrk_config in wrk_config_list:
        print(wrk_config)
    
    color_dict = {"SLATE": "blue", "WATERFALL": "red", "WATERFALL2": "red", "REMOTE": "green", "LOCAL": "orange"}
    cluster_map = dict()
    cid = 0
    for wrk_config in wrk_config_list:
        if wrk_config['cluster'] not in cluster_map:
            cluster_map[wrk_config['cluster']] = cid
            cid += 1
    print("cluster_map", cluster_map)
    for wrk_config in wrk_config_list:
        wrk_config['cluster_id'] = cluster_map[wrk_config['cluster']]
    wrk_config_list = sorted(wrk_config_list, key=lambda d: d['cluster'])
    if len(cluster_map) == 1:
        fig, axs = plt.subplots(2, 1, figsize=(5*len(cluster_map), 5))
    else:
        fig, axs = plt.subplots(1, len(cluster_map), figsize=(5*len(cluster_map), 5))
    fig.suptitle(' ', fontsize=30)
    # fig.suptitle('Latency CDF', fontsize=20)
    for wrk_config in wrk_config_list:
        print(wrk_config["cdf"])
        print(wrk_config["latencies_ms_sorted"])
        axs[cluster_map[wrk_config['cluster']]].plot(wrk_config["latencies_ms_sorted"], wrk_config["cdf"], marker='.', label=f"{wrk_config['routing_rule']}", color=color_dict[wrk_config['routing_rule']])

        title = f"{wrk_config['cluster']}, {wrk_config['RPS']} RPS"
        axs[cluster_map[wrk_config['cluster']]].set_title(title, fontsize=20)
        for ax in axs:
            ax.set_xlabel('Latency (ms)', fontsize=20)
            ax.set_ylabel('CDF', fontsize=20)
            ax.tick_params(axis='x', labelsize=15)
            ax.tick_params(axis='y', labelsize=15)
            # ax.set_xticks(fontsize=15)  # Set x-tick label fontsize
            # ax.set_yticks(np.arange(0,101,25))  # Set y-tick label fontsize
            ax.axhline(y=0.5, color='r', linestyle='--', linewidth=0.5, alpha=0.5)
            ax.axhline(y=0.90, color='r', linestyle='--', linewidth=0.5, alpha=0.5)
            ax.axhline(y=0.99, color='r', linestyle='--', linewidth=0.5, alpha=0.5)
    
    handles, labels = axs[0].get_legend_handles_labels()  # Assuming all subplots share the same legend
    print(labels)
    fig.legend(handles, labels, loc='upper center', bbox_to_anchor=(0.5,1.0), ncol=3, fontsize=16)
    plt.subplots_adjust(bottom=0.2)  # You might need to adjust this value
    plt.tight_layout()
    app_name = sys.argv[1].split('/')[0]
    experiment_tag = sys.argv[1].split('/')[-2]
    figure_file_path = f'{base_directory}/hit_cdf.pdf'
    plt.savefig(figure_file_path)
    print(f"Figure saved as {figure_file_path}")
    plt.show()