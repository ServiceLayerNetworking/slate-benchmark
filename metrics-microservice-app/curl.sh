cluster=$1
method=$2

node1="node1.gangmuk-186812.istio-pg0.utah.cloudlab.us"
node2="node2.gangmuk-186812.istio-pg0.utah.cloudlab.us"
nodeport=32288
#nodeport=32675

curl -v -H "x-slate-destination: ${cluster}" ${node1}:${nodeport}/start
