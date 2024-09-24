import pandas as pd
import matplotlib.pyplot as plt
import sys

# Load the CSV file
if __name__ == '__main__':
    if len(sys.argv) != 3:
        print('Usage: python plot_hillclimb.py <file_path> <out_pdf>')
        sys.exit(1)
    
    file_path = sys.argv[1]
    out_pdf = sys.argv[2]
    df = pd.read_csv(file_path)

    # Strip any leading/trailing spaces from the column names
    df.columns = df.columns.str.strip()

    # Convert 'time' column to datetime for better plotting
    df['time'] = pd.to_datetime(df['time'])

    # Create the figure and axis
    fig, ax1 = plt.subplots(figsize=(10, 6))

    # Group by 'podname'
    grouped = df.groupby('podname')

    # Plot avg_latency for each pod on the left y-axis
    for podname, group in grouped:
        ax1.plot(group['time'], group['avg_latency'], label=f'{podname} avg_latency')

    ax1.set_xlabel('Time')
    ax1.set_ylabel('Average Latency', color='blue')
    ax1.tick_params(axis='y', labelcolor='blue')

    # Create a second y-axis for new-us-west-1
    ax2 = ax1.twinx()

    # Plot new-us-west-1 for each pod on the right y-axis
    for podname, group in grouped:
        ax2.plot(group['time'], group['new-us-west-1'], label=f'{podname} new-us-west-1', linestyle='--')

    ax2.set_ylabel('New US West-1', color='green')
    ax2.tick_params(axis='y', labelcolor='green')

    # Set the limits of the secondary y-axis to 0 and 1
    ax2.set_ylim(0, 1)

    # Plot new-us-east-1 for each pod on the same left y-axis as avg_latency
    for podname, group in grouped:
        ax1.plot(group['time'], group['new-us-east-1'], label=f'{podname} new-us-east-1', linestyle=':')

    # Adding legends for both axes
    ax1.legend(loc='upper left', bbox_to_anchor=(1, 0.5), fontsize='small')
    ax2.legend(loc='upper right', bbox_to_anchor=(1, 1), fontsize='small')

    plt.title('New US East & West Latency and Pod-wise Average Latency Over Time')

    # Format x-axis for better readability
    plt.xticks(rotation=45)
    plt.tight_layout()

    # Save the figure as a PDF
    plt.savefig(out_pdf)
