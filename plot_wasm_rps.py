import os
import re
import sys
import matplotlib.pyplot as plt
from datetime import datetime

# Function to parse the log file and extract timestamps and middle values from inflightStats
def parse_log_file(filepath):
    timestamps = []
    middle_values = []

    with open(filepath, 'r') as file:
        in_inflight_stats = False
        for line in file:
            # Detect if we're in the inflightStats section
            if 'inflightStats' in line:
                in_inflight_stats = True
                continue
            
            # Stop reading inflightStats if we reach requestStats or other sections
            if 'requestStats' in line:
                in_inflight_stats = False
            
            # If in inflightStats, extract the time and the middle value
            if in_inflight_stats:
                # Try to match the time and the inflightStats entry format
                time_match = re.match(r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+Z)", line)
                inflight_match = re.search(r"POST@/cart,\d+,\d+\|", line)
                
                if time_match and inflight_match:
                    timestamp = datetime.strptime(time_match.group(1), "%Y-%m-%dT%H:%M:%S.%fZ")
                    timestamps.append(timestamp)

                    # Extract the middle value from the inflightStats entry
                    inflight_stats = inflight_match.group(0)
                    middle_value = int(inflight_stats.split(',')[1])
                    middle_values.append(middle_value)

    return timestamps, middle_values

# Function to plot the data and save it as a PDF
def plot_inflight_stats(timestamps, middle_values, output_filename):
    plt.figure(figsize=(10, 6))
    plt.plot(timestamps, middle_values, marker='o', linestyle='-', color='b')
    plt.xlabel('Time')
    plt.ylabel('Middle Value (inflightStats)')
    plt.title('InflightStats Middle Value Over Time')
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()

    # Save plot as a PDF
    print(f"Saving plot as {output_filename}")
    plt.savefig(output_filename, format='pdf')
    plt.close()

# Main function to handle parsing and plotting for all files in a directory
def process_directory(directory_path):
    for filename in os.listdir(directory_path):
        if filename.endswith(".log"):
            filepath = os.path.join(directory_path, filename)
            timestamps, middle_values = parse_log_file(filepath)
            if timestamps and middle_values:
                output_filename = f"{filename.replace('.log', '')}_inflight_stats.pdf"
                plot_inflight_stats(timestamps, middle_values, output_filename)
                print(f"Plot saved as {output_filename}")

# Entry point
if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python script_name.py <directory_path>")
        sys.exit(1)
    
    directory_path = sys.argv[1]
    if not os.path.isdir(directory_path):
        print(f"Error: {directory_path} is not a valid directory.")
        sys.exit(1)

    process_directory(directory_path)
