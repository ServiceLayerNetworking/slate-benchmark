# set -x
cluster=$1
path=$2

if [ -z "$cluster" ]; then
   echo "Usage: $0 <cluster> <path>"
   exit 1
fi
if [ -z "$path" ]; then
   echo "Usage: $0 <cluster> <path>"
   exit 1
fi

nodename=$(kubectl get nodes | grep "node1" | awk '{print $1}')
ingressgw_http2_nodeport=$(kubectl get svc istio-ingressgateway -n istio-system -o=json | jq '.spec.ports[] | select(.name=="http2") | .nodePort')
server_ip="http://${nodename}:${ingressgw_http2_nodeport}"
echo server_ip: $server_ip


st=$(date +%s)
for i in {1..1000} # total num requests
do
   start_time=$(date +%s%N)
   curl -XPOST -v -H "x-slate-destination: ${cluster}" ${server_ip}/${path}
   end_time=$(date +%s%N)
   duration=$(echo "scale=4; ($end_time - $start_time) / 1000000" | bc)

   # sleep_time_in_ms=$(echo "scale=4; 1000 - $duration" | bc) # 1 RPS
   sleep_time_in_ms=$(echo "scale=4; 100 - $duration" | bc) # 10 RPS
   # sleep_time_in_ms=$(echo "scale=4; 10 - $duration" | bc) # 100 RPS

   sleep_time_in_second=$(echo "scale=4; $sleep_time_in_ms / 1000" | bc)
   sleep ${sleep_time_in_second}
   echo "Duration: ${duration} ms"
   echo "Sleep millisecond time: ${sleep_time_in_ms} ms"
   echo "Sleep second time: ${sleep_time_in_second} s"
done
et=$(date +%s)
total_time=$(echo "scale=2; ($et - $st)" | bc)
echo "Total time: ${total_time} seconds"