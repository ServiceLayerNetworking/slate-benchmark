import matplotlib.pyplot as plt
import pandas as pd
import sys

def plot_rps(csv_file_path):
    # Load the data into a DataFrame directly from a file
    df = pd.read_csv(csv_file_path)
    df.columns = df.columns.str.strip()
    # print(df.columns)
    # print(df.head())
    # Group by 'region' and 'service' to plot each as a separate line
    
    # services_to_plot = ['metrics-fake-ingress', 'metrics-handler']
    services_to_plot = ['metrics-fake-ingress']
    df = df[df['service'].str.strip().isin(services_to_plot)]
    
    grouped_data = df.groupby(['region', 'service'])

    # Initialize a plot
    plt.figure(figsize=(10, 7))

    # Plot each group
    for (region, service), group in grouped_data:
        plt.plot(group['counter'], group['rps'], label=f'{region} - {service}')

    # Enhance the plot
    plt.title('RPS over time')
    plt.xlabel('Time (roughly 1 second tick)')
    plt.ylabel('RPS')
    plt.legend(title='Region - Service', bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.grid(True)

    # Display the plot
    plt.tight_layout()
    routing_rule = csv_file_path.split("/")[-1].split("-")[0]
    pdf_file = f'{routing_rule}-rps_over_time.pdf'
    plt.savefig(pdf_file)
    print(f"Plot saved as {pdf_file}")
    plt.show()

    

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python script_name.py <path_to_csv_file>")
        sys.exit(1)
    
    csv_file_path = sys.argv[1]
    plot_rps(csv_file_path)
