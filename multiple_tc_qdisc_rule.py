import os
import subprocess
from datetime import datetime
from kubernetes import client, config
import math
import time
import concurrent.futures
import sys
import os
import concurrent.futures
from datetime import datetime
import copy
import xml.etree.ElementTree as ET
from pprint import pprint


def parse_xml(file_path):
    # Load and parse the XML file
    tree = ET.parse(file_path)
    return tree.getroot()

def extract_node_info(root, namespaces):
    # Extract node names and their IPv4 addresses
    nodes = root.findall('.//ns:node', namespaces)
    nodes_info = [
        (
            node.get('client_id'),
            # node.find('.//ns:host', namespaces).get('name'),
            [login.get('hostname') for login in node.findall('.//ns:services/ns:login', namespaces)][0],
            node.find('.//ns:host', namespaces).get('ipv4')
        )
        for node in nodes if node.find('.//ns:host', namespaces) is not None
    ]
    node_dict = {}
    for node, hostname, ipaddr in nodes_info:
        node_dict[node] = {"hostname": hostname, "ipaddr": ipaddr}
    return node_dict

def get_nodename_and_ipaddr(file_path):
    namespaces = {
        'ns': 'http://www.geni.net/resources/rspec/3',
    }
    
    root = parse_xml(file_path)
    return extract_node_info(root, namespaces)

def run_command(command):
    """Run shell command and return its output and error if any."""
    try:
        output = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT)
        return output.decode('utf-8').strip(), None
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {command}\nerror: {e.output.decode('utf-8').strip()}")
        return None, e.output.decode('utf-8').strip()

def add_latency_rules(src_host, interface, dst_node_ip, delay):
    class_id = f"1:{delay}"
    handle_id = delay
    run_command(f'ssh {src_host} sudo tc class add dev eno1 parent 1: classid {class_id} htb rate 100mbit')
    run_command(f'ssh {src_host} sudo tc qdisc add dev eno1 parent {class_id} handle {handle_id}: netem delay {delay}ms')
    run_command(f'ssh {src_host} sudo tc filter add dev eno1 protocol ip parent 1:0 prio 1 u32 match ip dst {dst_node_ip} flowid {class_id}')
        
def main():
    '''
    node1: west
    node2: east
    node3: central
    
    node_dict[node1] = {"hostname": hostname, "ipaddr": ipaddr}
    '''
    node_dict = get_nodename_and_ipaddr("/users/gangmuk/projects/cloudlab_script/config.xml")
    for node in node_dict:
        print(f"node: {node}, hostname: {node_dict[node]['hostname']}, ipaddr: {node_dict[node]['ipaddr']}")
        
    node_to_region = {"node1":"us-west-1", "node2":"us-east-1", "node3":"us-central-1", "node4":"us-south-1"}
    
    inter_cluster_latency = dict()
    for src_node in node_to_region:
        inter_cluster_latency[src_node] = dict()
    inter_cluster_latency["node1"]["node2"] = 20 # west, east
    inter_cluster_latency["node1"]["node3"] = 20 # west, central
    inter_cluster_latency["node1"]["node4"] = 20 # west, south
    inter_cluster_latency["node2"]["node3"] = 10 # east, central
    inter_cluster_latency["node2"]["node4"] = 10 # east, south
    inter_cluster_latency["node3"]["node4"] = 10 # central, south
    for src_node in inter_cluster_latency:
        for dst_node in inter_cluster_latency[src_node]:
            if src_node == dst_node:
                continue
            inter_cluster_latency[dst_node][src_node] = inter_cluster_latency[src_node][dst_node]
    print("inter_cluster_latency")
    pprint(inter_cluster_latency)
    
    for node in node_dict:
        run_command(f"ssh {node_dict[node]['hostname']} sudo tc qdisc del dev eno1 root")
        print(f"delete tc qdisc rule in {node_dict[node]['hostname']}")
    interface = "eno1"  # Ensure this is the correct interface
    src_host = "apt178.apt.emulab.net" # node1
    '''inter_cluster_latency["node1"]["node2"] = 40'''
    for src_node in inter_cluster_latency:
        src_host = node_dict[src_node]['hostname']
        run_command(f'ssh {src_host} sudo tc qdisc add dev eno1 root handle 1: htb')
        for dst_node in inter_cluster_latency[src_node]:
            if src_node == dst_node:
                continue
            dst_node_ip = node_dict[dst_node]['ipaddr'] 
            delay = inter_cluster_latency[src_node][dst_node]
            add_latency_rules(src_host, interface, dst_node_ip, delay)
            print(f"from {src_host}({src_node}) to {dst_node_ip}({dst_node}), {delay}ms")

if __name__ == "__main__":
    main()
