cluster=$1
method=$2

nodename=$(kubectl get nodes | grep "node1" | awk '{print $1}')
ingressgw_http2_nodeport=$(kubectl get svc istio-ingressgateway -n istio-system -o=json | jq '.spec.ports[] | select(.name=="http2") | .nodePort')
server_ip="http://${nodename}:${ingressgw_http2_nodeport}"
echo $server_ip


curl -v -H "x-slate-destination: ${cluster}" ${server_ip}/start
