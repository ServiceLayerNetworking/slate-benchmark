cluster=$1
method=$2

nodename=$(kubectl get nodes | grep "node1" | awk '{print $1}')
ingressgw_http2_nodeport=$(kubectl get svc istio-ingressgateway -n istio-system -o=json | jq '.spec.ports[] | select(.name=="http2") | .nodePort')
server_ip="http://${nodename}:${ingressgw_http2_nodeport}"
echo $server_ip


if [ $cluster == "west" ]; then
    if [ $method == "get" ]; then
        curl -v -X ${method} -H "x-slate-destination: west" ${server_ip}/compute\?row\=2\&column\=2
    elif [ $method == "post" ]; then
        curl -v -X ${method} -H "x-slate-destination: west" ${server_ip}/compute\?row\=1000\&column\=1000
    fi
elif [ $cluster == "east" ]; then
    if [ $method == "get" ]; then
        curl -v -X ${method} -H "x-slate-destination: east" ${server_ip}/compute\?row\=2\&column\=2
    elif [ $method == "post" ]; then
        curl -v -X ${method} -H "x-slate-destination: east" ${server_ip}/compute\?row\=1000\&column\=1000
    fi
fi
