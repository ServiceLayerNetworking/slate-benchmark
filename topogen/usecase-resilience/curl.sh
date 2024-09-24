cluster=$1
method=get
#method=$2

if [ -z "$cluster" ]; then
   echo "Usage: $0 <cluster>"
   echo "Example: ./curl.sh west"
   exit 1
fi

nodename=$(kubectl get nodes | grep "node2" | awk '{print $1}')
ingressgw_http2_nodeport=$(kubectl get svc istio-ingressgateway -n istio-system -o=json | jq '.spec.ports[] | select(.name=="http2") | .nodePort')
server_ip="http://${nodename}:${ingressgw_http2_nodeport}"
echo server_ip: $server_ip
curl -v -H "x-slate-destination: ${cluster}" ${server_ip}/start
echo

exit

# for i in {1..50}
# do
#    echo "Iteration number $i"
#    curl -v -H "x-slate-destination: ${cluster}" ${server_ip}/start &
# done
