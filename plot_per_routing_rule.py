import re
import sys
import glob
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import subprocess
import itertools
import time

default_colors = plt.rcParams['axes.prop_cycle'].by_key()['color']
req_type = ""

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

def parse_latency_stat_in_wrklog_file(wrklog_path, wrk_config, latency_metrics, latency_dict, stat_dict, rps_thr=99999):
    latency_patterns = regex_pattern(latency_metrics)
    with open(wrklog_path, 'r') as file:
        wrklog_file_read = file.read()
        
        pattern = r"reconnect_socket"
        match = re.search(pattern, wrklog_file_read)
        if match:
            print("WARNING: reconnect_socket exists")

        
        #########################################
        pattern = r"Requests/sec:\s*(\d+\.\d+)"
        match = re.search(pattern, wrklog_file_read)
        if match:
            tput = float(match.group(1))
            print(f"{wrk_config['routing_rule']}, {wrk_config['cluster']}, {wrk_config['req_type']}, {wrk_config['RPS']}, Actual tput: {tput}, Gap: {int(float(wrk_config['RPS']) - tput)}")
        else:
            print("Pattern not found")
            print(wrklog_path)
            assert False
        #########################################
        # print(wrk_config)
        # rps_value = int(wrk_config[f"{cluster}_RPS"])
        rps_value = int(wrk_config[f"RPS"])
        if rps_value <= rps_thr:
            latency_dict["rps"].append(rps_value)
            latency_dict["mode"].append(wrk_config["mode"])
            latency_dict["routing_rule"].append(wrk_config["routing_rule"])
            latency_dict["jumping"].append(wrk_config["jumping"])
            latency_dict["cluster"].append(wrk_config["cluster"])
            latency_dict["tput"].append(tput)
            
            if wrk_config["routing_rule"] not in stat_dict:
                stat_dict[wrk_config["routing_rule"]] = dict()
            if str(rps_value) not in stat_dict[wrk_config["routing_rule"]]:
                stat_dict[wrk_config["routing_rule"]][str(rps_value)] = dict()
            if wrk_config["cluster"] not in stat_dict[wrk_config["routing_rule"]][str(rps_value)]:
                stat_dict[wrk_config["routing_rule"]][str(rps_value)][wrk_config["cluster"]] = dict()
                
            for target_metric, pattern in latency_patterns.items():
                latency_value = find_latency_value(pattern, wrklog_file_read)
                # print(f"target_metric: {target_metric}, latency_value: {latency_value}")
                if target_metric not in latency_dict:
                    latency_dict[target_metric] = []
                try:
                    stat_dict[wrk_config["routing_rule"]][str(rps_value)][wrk_config["cluster"]][target_metric] = float(latency_value)
                except Exception as e:
                    print(f"Error: {e}")
                    print(f"target_metric: {target_metric}, latency_value: {latency_value}")
                    print(wrklog_path)
                    print()
                    assert False
                latency_dict[target_metric].append(latency_value)
        
def find_and_process_wrklog_files(base_directory):
    wrklog_files = glob.glob(f'{base_directory}/**/*.wrklog', recursive=True)
    return wrklog_files

#####################################################################################################

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
                match = re.match(r"\s*(\d+\.\d+)\s+(\d+\.\d+)\s+(\d+)", line)
                if match:
                    value, percentile, total_count = match.groups()
                    cdf_data.append((float(value), float(percentile), int(total_count)))
    return cdf_data


def find_and_process_wrklog_files(base_directory):
    wrklog_files = glob.glob(f'{base_directory}/**/*.wrklog', recursive=True)
    # for file in wrklog_files:
    #     print(file)
    return wrklog_files


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python plot_per_routing_rule.py <base_directory>")
        print("Example 1: python plot_per_routing_rule.py online-boutique/partial-C_cart/W400-E100-C100-S100")
        print("Example 2: python plot_per_routing_rule.py online-boutique/test-bg20")
        sys.exit(1)

    base_directory = sys.argv[1]
    wrklog_files = find_and_process_wrklog_files(base_directory)

    # Collect configurations
    wrk_config_list = []
    for wrklog_path in wrklog_files:
        print(f"Processing {wrklog_path}")
        wrk_config = parse_wrk_config(wrklog_path)
        wrk_config['percentile_data'] = extract_cdf_data(wrklog_path)
        wrk_config_list.append(wrk_config)
        
        
    # Initialize dictionaries for stats and latency data aggregation
    latency = {}
    count = {}
    xlim_right = 0
    '''
    one wrk_config represents one wrklog file
    '''
    for wrk_config in wrk_config_list:
        percentile_df = pd.DataFrame(wrk_config["percentile_data"], columns=['Value', 'Percentile', 'TotalCount'])
        percentile_df['Percentile'] *= 100
        
        '''
        To plot multiple waterfall algorithm, you should use WF(capacity) as the key.
        WATERFALL key will overwrite the previous WATERFALL key.
        Eventually, there must be one WATERFALL in the plot.
        '''
        if "WATERFALL" in wrk_config['routing_rule']:
            key = f"WF({wrk_config['capacity']})"
            # key = "WATERFALL"
        else:
            key = wrk_config['routing_rule']
        
        
        '''
        Skip some capacity in waterfall
        If you don't want to skip any, comment out the following block
        '''
        skip_local_routing_plot = False
        if skip_local_routing_plot:
            if wrk_config['routing_rule'] == 'LOCAL':
                print("Skip LOCAL routing in this plot")
                continue
        
        '''
        Skip some capacity in waterfall
        If you don't want to skip any, comment out the following block
        '''
        skip_waterfall_capacity = []
        # skip_waterfall_capacity = [700, 1000]
        if wrk_config['routing_rule'] == "WATERFALL2" and wrk_config['capacity'] in skip_waterfall_capacity:
            print(f"Skip WATERFALL2 capacity={wrk_config['capacity']} in this plot")
            continue
        
        '''Add jumpingn to the routing rule key'''
        if "jumping" in wrk_config:
            if wrk_config['jumping'] == 1 or wrk_config['jumping'] == "1":
                key += "-with-jumping"
            else:
                key += "-without-jumping"
        
        ''' Use it when you want to plot per cluster as well'''
        if "cluster" in wrk_config:
            key += f"-{wrk_config['cluster']}"
            
        
        if "LOCAL" in wrk_config['routing_rule']:
            xlim_right = max(xlim_right, percentile_df['Value'].max())

        ## Aggregate data across all request types
        previous_total_count = 0
        for index, row in percentile_df.iterrows():
            if key not in latency:
                latency[key] = []
                count[key] = []
            
            absolute_count = row['TotalCount'] - previous_total_count
            previous_total_count = row['TotalCount']    
            
            latency[key].append(row['Value'])
            # count[key].append(int(row['TotalCount']))
            count[key].append(absolute_count)
            

    # Plotting
    plt.figure(figsize=(4.5, 4))
    for key in sorted(latency.keys()):
        weighted_latencies = np.repeat(latency[key], count[key])
        sorted_data = np.sort(weighted_latencies)
        cdf = np.arange(1, len(sorted_data) + 1) / len(sorted_data)
        
        ######################################
        ## plot coloring
        # if "SLATE" in key:
        #     # linestyle = '-'
        #     # color = default_colors[0]
        #     color = "blue"
        # # elif "WATERFALL" in key or "WF" in key:
        # #     # linestyle = 'dashed'
        # #     # linestyle = (5, (10, 3)) # long dash with offset
        # #     # color = default_colors[1]
        # #     color = 'red'
        # elif "LOCAL" in key:
        #     # linestyle = ':'
        #     color = 'green'
        # else:
        #     print(f"Unknown routing_rule: {key}")
        #     # assert False
        ######################################
        
        avg_latency = int(np.mean(sorted_data))
        p99_latency = int(np.percentile(sorted_data, 99))
        p999_latency = int(np.percentile(sorted_data, 99.9))
        # print(key)
        print(f"[statistics],{key},avg,{avg_latency},p99,{p99_latency},p999,{p999_latency}")
        
        ## No Color
        plt.plot(sorted_data, cdf, label=key, linewidth=1.2)
        # plt.plot(sorted_data, cdf, label=key, linewidth=1.2, color=color)

    plt.xlabel('Latency (ms)', fontsize=18)
    plt.xticks(fontsize=14, rotation=-45)
    plt.yticks(fontsize=14)
    plt.grid(True)

    legend_fontsize = 8
    try:
        order_legend = "by_string" # "by_index", "by_string", False
        if order_legend == "by_index":
            # Order: LOCAL, WATERFALL, SLATE
            handles, labels = plt.gca().get_legend_handles_labels()
            order = [1,2,0]
            print(f"WARNING: It will only plot the first three routing rules")
            print(f"WARNING: It will only plot the first three routing rules")
            print(f"WARNING: It will only plot the first three routing rules")
            time.sleep(3)
            plt.legend([handles[idx] for idx in order],[labels[idx] for idx in order], fontsize=12, loc='lower right')
        elif order_legend == "by_string":
            # Order by string: LOCAL, SLATE, WF(1000), WF(1500), WF(700)
            handles, labels = plt.gca().get_legend_handles_labels()
            sorted_pairs = sorted(zip(handles, labels), key=lambda x: x[1])
            sorted_handles, sorted_labels = zip(*sorted_pairs)
            plt.legend(sorted_handles, sorted_labels, fontsize=legend_fontsize, loc='lower right')
        else:
            plt.legend(fontsize=legend_fontsize, loc='lower right')
    except:
        print("less than three routing rules. default legend")
        plt.legend(fontsize=legend_fontsize, loc='lower right')
    
    plt.ylim(0, 1.01)
    plt.xlim(left=0)
    if xlim_right > 1000:
        xlim_right = 1000
        plt.xlim(right=xlim_right)
    plt.tight_layout()
    plt.savefig(f'{base_directory}/routing_rules_cdf.pdf')
    print(f"Output PDF saved to: {base_directory}/routing_rules_cdf.pdf")
    plt.show()