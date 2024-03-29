import matplotlib.pyplot as plt
import pandas as pd
import sys

def plot_rps(csv_file_path, services_to_plot):
    # Load the data into a DataFrame directly from a file
    df = pd.read_csv(csv_file_path)
    df.columns = df.columns.str.strip()
    # print(df.columns)
    # print(df.head())
    # Group by 'region' and 'service' to plot each as a separate line
    
    # services_to_plot = ['metrics-fake-ingress', 'metrics-handler']
    df = df[df['service'].str.strip().isin(services_to_plot)]
    df = df.applymap(lambda x: x.strip() if isinstance(x, str) else x)

    grouped_data = df.groupby(['region', 'service'])

    # Initialize a plot
    plt.figure(figsize=(10, 7))

    # Plot each group
    linestyle_map = {"metrics-fake-ingress": "-", "metrics-handler": "--"}
    color_dict = {"us-west-1": "blue", "us-central-1": "orange", "us-south-1": "red", "us-east-1": "green"}
    for (region, service), group in grouped_data:
        plt.plot(group['counter'], group['rps'], label=f'{region} - {service}', linestyle=linestyle_map[service], color=color_dict[region])

    # Enhance the plot
    plt.title('RPS over time')
    plt.xlabel('Time (roughly 1 second tick)')
    plt.ylabel('RPS')
    # plt.legend(title='Region - Service', bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.legend(title='Region - Service')
    plt.grid(True)

    # plt.xlim(127, 132)
    # plt.xlim([120,None])
    # Display the plot
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
    
    # services_to_plot = ['metrics-fake-ingress']
    services_to_plot = ['metrics-fake-ingress', 'metrics-handler']
    plot_rps(csv_file_path, services_to_plot)
