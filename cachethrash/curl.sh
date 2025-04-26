# cluster=$1
cluster=west
method=post
#method=$2

if [ -z "$cluster" ]; then
   echo "Usage: $0 <cluster>"
   echo "Example: ./curl.sh west"
   exit 1
fi

nodename=$(kubectl get nodes | grep "node0" | awk '{print $1}')
ingressgw_http2_nodeport=$(kubectl get svc istio-ingressgateway -n istio-system -o=json | jq '.spec.ports[] | select(.name=="http2") | .nodePort')
server_ip="http://${nodename}:${ingressgw_http2_nodeport}"
echo server_ip: $server_ip

#curl -v -XPOST -H "x-slate-destination: ${cluster}" "${server_ip}/cart/empty"

# curl -v -XPOST -H "x-slate-destination: ${cluster}" "${server_ip}/cart?product_id=OLJCESPC7Z&quantity=5"

# checkout cart
curl -v -XGET -H "x-slate-destination: ${cluster}" "${server_ip}/getRecord/2"

echo

exit
