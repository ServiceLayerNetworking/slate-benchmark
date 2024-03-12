import re
import sys
import glob
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

latency_dict = dict()
req_type = ""

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

def plot_cdf(data, parse_wrk_config):
    '''
    data = [(value, percentile), ...]
    '''
    
    # plt.savefig('cdf.png')
    # plt.show()



if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python script.py <input_files> ")
        sys.exit(1)
    columns = ['avg', '50%', '99%']
    wrk_config_list = list()
    for pattern in sys.argv[1:]:
        for wrklog_path in glob.glob(pattern):
            config = parse_wrk_config(wrklog_path)
            config["percentile_data"] = extract_cdf_data(wrklog_path)
            wrk_config_list.append(config)
            
    fig, axs = plt.subplots(1, 2, figsize=(10, 5))
    fig.suptitle('Latency CDF', fontsize=20)
    for config in wrk_config_list:
        df = pd.DataFrame(config["percentile_data"], columns=['Value', 'Percentile'])
        df['Percentile'] *= 100
        if config['routing_rule'] != "REMOTE":
            title = f"{config['cluster']}, {config['RPS']} RPS"
            if config['cluster'] == 'west':
                axs[0].plot(df['Value'], df['Percentile'], linestyle='-', label=f"{config['routing_rule']}, {config['cluster']}")
                axs[0].set_title(title, fontsize=20)
            else:
                axs[1].plot(df['Value'], df['Percentile'], linestyle='-', label=f"{config['routing_rule']}, {config['cluster']}")
                axs[1].set_title(title, fontsize=20)
        
            for ax in axs:
                ax.set_xlabel('Latency (ms)', fontsize=20)
                ax.set_ylabel('Percentile (%)', fontsize=20)
                ax.tick_params(axis='x', labelsize=15)
                ax.tick_params(axis='y', labelsize=15)
                # ax.set_xticks(fontsize=15)  # Set x-tick label fontsize
                ax.set_yticks(np.arange(0,101,25))  # Set y-tick label fontsize
                ax.legend(fontsize=15)
                ax.axhline(y=50, color='r', linestyle='--', linewidth=0.5, alpha=0.5)
                ax.axhline(y=90, color='r', linestyle='--', linewidth=0.5, alpha=0.5)
                ax.axhline(y=99, color='r', linestyle='--', linewidth=0.5, alpha=0.5)
    # plt.xlim((0,1000))
    plt.tight_layout()
    app_name = sys.argv[1].split('/')[0]
    experiment_tag = sys.argv[1].split('/')[-2]
    figure_file_name = f'{app_name}-{experiment_tag}.pdf'
    plt.savefig(figure_file_name)
    print(f"Figure saved as {figure_file_name}")
    plt.show()