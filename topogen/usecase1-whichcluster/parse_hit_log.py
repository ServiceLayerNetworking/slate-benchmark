import json
import numpy as np
import matplotlib.pyplot as plt
import argparse
import sys

def parse_latencies_from_file(file_path):
    latencies_ns = []
    with open(file_path, 'r') as file:
        next(file)
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
    return latencies_ns

def plot_cdf(latencies_ns):
    latencies_ns_sorted = np.sort(latencies_ns)
    cdf = np.arange(1, len(latencies_ns_sorted) + 1) / len(latencies_ns_sorted)

    plt.figure(figsize=(8, 6))
    plt.plot(latencies_ns_sorted, cdf, marker='.', linestyle='none')
    plt.xlabel('Latency in Nanoseconds')
    plt.ylabel('CDF')
    plt.title('CDF of Latencies')
    plt.grid(True)
    plt.savefig('latency_cdf.png')
    print("CDF plot saved as 'latency_cdf.png'")
    plt.show()


if __name__ == "__main__":
    # parser = argparse.ArgumentParser(description="Parse latency data from a file and plot CDF.")
    # parser.add_argument("file_path", type=str, help="The file path to the JSON file containing the latency data.")
    # args = parser.parse_args()
    
    file_path = sys.argv[1]
    # latencies_ns = parse_latencies_from_file(args.file_path)
    latencies_ns = parse_latencies_from_file(file_path)
    plot_cdf(latencies_ns)
