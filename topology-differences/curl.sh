cluster=west
method=get
#cluster=$1
#method=$2

nodename=$(kubectl get nodes | grep "node2" | awk '{print $1}')
ingressgw_http2_nodeport=$(kubectl get svc istio-ingressgateway -n istio-system -o=json | jq '.spec.ports[] | select(.name=="http2") | .nodePort')
server_ip="http://${nodename}:${ingressgw_http2_nodeport}"
echo server_ip: $server_ip
curl -v -H "x-slate-destination: west" ${server_ip}/start
echo
echo "curl -v -H \"x-slate-destination: west\" ${server_ip}/start"

exit

for i in {1..50}
do
   echo "Iteration number $i"
   curl -v -H "x-slate-destination: west" ${server_ip}/start &
done

#for i in {1..10}
#do
#   echo "Iteration number $i"
#   curl -v -H "x-slate-destination: east" ${server_ip}/start
#done
