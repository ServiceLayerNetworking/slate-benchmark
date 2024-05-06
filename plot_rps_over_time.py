import matplotlib.pyplot as plt
import pandas as pd
import sys

def plot_rps(csv_file_path, services_to_plot):
    # Load the data into a DataFrame directly from a file
    df = pd.read_csv(csv_file_path)
    df.columns = df.columns.str.strip()
    
    # df = df[df['service'].str.strip().isin(services_to_plot)]
    df = df[df['endpoint'].str.strip().isin(services_to_plot)]
    
    df = df.applymap(lambda x: x.strip() if isinstance(x, str) else x)
    df = df[df['rps'] > 0]
    starting_point = 20
    df = df[df['counter'] > starting_point]
    df['counter'] = df['counter'] - starting_point
    
    # grouped_data = df.groupby(['region', 'service'])
    grouped_data = df.groupby(['region', 'endpoint'])
    
    # plt.figure(figsize=(10, 7))
    linestyle_map = dict()
    for i in range(len(services_to_plot)):
        if i == 0:
            linestyle_map[services_to_plot[i]] = "-"
        else:
            linestyle_map[services_to_plot[i]] = ":"
            
    color_dict = {"us-west-1": "blue", "us-central-1": "orange", "us-south-1": "red", "us-east-1": "green"}
    for (region, service), group in grouped_data:
        # plt.plot(group['counter'], group['rps'], label=f'{region} - {service}', linestyle=linestyle_map[service], color=color_dict[region], linewidth=0.8)
        # print(group['counter'].tolist())
        # label=f'{region} - {service}'
        label=f'{region}'
        plt.plot(group['counter'], group['rps'], label=label, linestyle=linestyle_map[service], color=color_dict[region], linewidth=1)
    # plt.title('RPS over time')
    plt.xlim(left=0)
    plt.ylim(bottom=0)
    # plt.xticks(fontsize=18)
    plt.xticks(range(int(group['counter'].min())+1, int(group['counter'].max()) + 1, 2), rotation=90, fontsize=12)
    plt.yticks(fontsize=14)
    plt.xlabel('Time (seconds)', fontsize=18)
    plt.ylabel('Load', fontsize=18)
    # plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=8)
    plt.legend(loc='upper left', fontsize=14)
    plt.grid(True)
    # plt.xlim(127, 132)
    # plt.xlim([120,None])
    plt.tight_layout()
    routing_rule = csv_file_path.split("/")[-1].split("-")[0]
    dir = csv_file_path.split("/")[:-1]
    dir = ("/").join(dir)
    pdf_file = f'{dir}/{routing_rule}-rps_over_time.pdf'
    plt.savefig(pdf_file)
    print(f"Plot saved as {pdf_file}")
    plt.show()
    

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python script_name.py <path_to_csv_file>")
        sys.exit(1)
    csv_file_path = sys.argv[1]
    # metrics
    # services_to_plot = ['metrics-fake-ingress', 'metrics-handler']
    # # spread
    # services_to_plot = ['frontend', 'a']
    # services_to_plot = ['slateingress', 'frontend']
    # services_to_plot = ['sslateingress', 'frontend']
    
    # sslateingress,sslateingress@POST@/cart,427
    # sslateingress,sslateingress@POST@/cart/empty,429
    # sslateingress,sslateingress@POST@/setCurrency,444
    # sslateingress,sslateingress@POST@/cart/checkout,426
    
    # services_to_plot = ['sslateingress@POST@/cart/checkout', 'frontend@POST@/cart/checkout']
    services_to_plot = ['frontend@POST@/cart/checkout']
    plot_rps(csv_file_path, services_to_plot)
