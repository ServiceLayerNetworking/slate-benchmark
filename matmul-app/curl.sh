method=$1
cluster=$2

if [ $cluster == "west" ]; then
    if [ $method == "GET" ]; then
        curl -v -X ${method} -H "x-slate-destination: west" http://node1.gangmuk-185120.istio-pg0.clemson.cloudlab.us:30763/compute\?row\=2\&column\=2
    elif [ $method == "POST" ]; then
        curl -v -X ${method} -H "x-slate-destination: west" http://node1.gangmuk-185120.istio-pg0.clemson.cloudlab.us:30763/compute\?row\=1000\&column\=1000
    fi
elif [ $cluster == "east" ]; then
    if [ $method == "GET" ]; then
        curl -v -X ${method} -H "x-slate-destination: east" http://node2.gangmuk-185120.istio-pg0.clemson.cloudlab.us:30763/compute\?row\=2\&column\=2
    elif [ $method == "POST" ]; then
        curl -v -X ${method} -H "x-slate-destination: east" http://node2.gangmuk-185120.istio-pg0.clemson.cloudlab.us:30763/compute\?row\=1000\&column\=1000
    fi
fi
