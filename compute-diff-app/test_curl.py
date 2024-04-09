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
import atexit
import signal
import requests

def run_command(command, required=True, print_error=True, nonblock=False):
    """Run shell command and return its output"""
    try:
        ''' Popen is asynchronous and non-blocking, while check_output is synchronous and blocking.'''
        if nonblock:
            process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            stdout, stderr = process.communicate()  # If you decide to wait and capture output for debugging
            print("STDOUT:", stdout)
            print("STDERR:", stderr)
            return True, "NotOutput-this-is-nonblocking-execution"
        else:
            output = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT)
            return True, output.decode('utf-8').strip()
    except subprocess.CalledProcessError as e:
        if print_error:
            print(f"ERROR command: {command}")
            print(f"ERROR output: {e.output.decode('utf-8').strip()}")
        if required:
            print("Exit...")
            assert False
        else:
            return False, e.output.decode('utf-8').strip()

success, nodename = run_command("kubectl get nodes | grep 'node1' | awk '{print $1}'")
success, ingressgw_http2_nodeport = run_command("kubectl get svc istio-ingressgateway -n istio-system -o=json | jq '.spec.ports[] | select(.name==\"http2\") | .nodePort'")
server_ip = f"http://{nodename}:{ingressgw_http2_nodeport}"
print(f"server_ip: {server_ip}")


rps = {"west": {"write1kb": 100, "write1mb": 100}, "east": {"write1kb": 100, "write1mb": 100}}

