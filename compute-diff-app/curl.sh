set -x
cluster=$1
method=get
#method=$2

if [ -z "$cluster" ]; then
   echo "Usage: $0 <cluster>"
   exit 1
fi

nodename=$(kubectl get nodes | grep "node1" | awk '{print $1}')
ingressgw_http2_nodeport=$(kubectl get svc istio-ingressgateway -n istio-system -o=json | jq '.spec.ports[] | select(.name=="http2") | .nodePort')
server_ip="http://${nodename}:${ingressgw_http2_nodeport}"
echo server_ip: $server_ip

curl -XPOST -v -H "x-slate-destination: ${cluster}" ${server_ip}/write1kb # 4ms
# curl -XPOST -v -H "x-slate-destination: ${cluster}" ${server_ip}/write10kb # 5ms
# curl -XPOST -v -H "x-slate-destination: ${cluster}" ${server_ip}/write100kb # 6ms
# curl -XPOST -v -H "x-slate-destination: ${cluster}" ${server_ip}/write1mb # 10ms
# curl -XPOST -v -H "x-slate-destination: ${cluster}" ${server_ip}/write2mb # 14ms
# curl -XPOST -v -H "x-slate-destination: ${cluster}" ${server_ip}/write4mb # 25ms

# curl_command="curl -XPOST -v -H x-slate-destination: ${cluster} ${server_ip}/write1kb"
# echo "** curl_command: ${curl_command}"

# for i in {1..50}
# do
#    echo "Iteration number $i"
#    curl -v -H "x-slate-destination: ${cluster}" ${server_ip}/start &
# done
