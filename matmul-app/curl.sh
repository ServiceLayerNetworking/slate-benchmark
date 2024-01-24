cluster=$1
method=$2

node1="node1.gangmuk-186812.istio-pg0.utah.cloudlab.us"
node2="node2.gangmuk-186812.istio-pg0.utah.cloudlab.us"
nodeport=30277
#nodeport=31024


if [ $cluster == "west" ]; then
    if [ $method == "GET" ]; then
        curl -v -X ${method} -H "x-slate-destination: west" ${node1}:${nodeport}/compute\?row\=2\&column\=2
    elif [ $method == "POST" ]; then
        curl -v -X ${method} -H "x-slate-destination: west" ${node1}:${nodeport}/compute\?row\=1000\&column\=1000
    fi
elif [ $cluster == "east" ]; then
    if [ $method == "GET" ]; then
        curl -v -X ${method} -H "x-slate-destination: east" ${node2}:${nodeport}/compute\?row\=2\&column\=2
    elif [ $method == "POST" ]; then
        curl -v -X ${method} -H "x-slate-destination: east" ${node2}:${nodeport}/compute\?row\=1000\&column\=1000
    fi
fi
