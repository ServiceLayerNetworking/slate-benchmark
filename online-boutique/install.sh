set -x

num_regions=$1
if [ -z $num_regions ]; then
    echo "Usage: ./install.sh <num_regions>"
    exit 1
fi
if [ $num_regions -eq 2 ]; then
    regions="us-west-1,us-east-1"
elif [ $num_regions -eq 3 ]; then
    regions="us-west-1,us-east-1,us-central-1"
elif [ $num_regions -eq 4 ]; then
    regions="us-west-1,us-east-1,us-central-1,us-south-1"
else
    echo "Invalid number of regions. Please enter 2, 3, or 4"
    exit 1
fi

echo "It assumes that k8s is clean without anything installed or configured"
echo "If you want to delete all k8s resources, refer to /users/gangmuk/projects/slate-benchmark/delete_all_k8s_resources.sh"

echo \n"will start in 5 seconds"
echo regions: ${regions}
sleep 5

repo_dir="/users/gangmuk/projects/slate-benchmark"

nodes_with_labels=$(kubectl get nodes --show-labels)
node1=$(echo "$nodes_with_labels" | grep 'node1' | awk '{print $1}')
node2=$(echo "$nodes_with_labels" | grep 'node2' | awk '{print $1}')
kubectl label node $node1 topology.kubernetes.io/zone=us-west-1 --overwrite
kubectl label node $node2 topology.kubernetes.io/zone=us-east-1 --overwrite
echo "kubectl label node $node1 topology.kubernetes.io/zone=us-west-1 --overwrite"
echo "kubectl label node $node2 topology.kubernetes.io/zone=us-east-1 --overwrite"
if [ $num_regions -ge 3 ]; then
    node3=$(echo "$nodes_with_labels" | grep 'node3' | awk '{print $1}')
    kubectl label node $node3 topology.kubernetes.io/zone=us-central-1 --overwrite
    echo "kubectl label node $node3 topology.kubernetes.io/zone=us-central-1 --overwrite"
fi

if [ $num_regions -ge 4 ]; then
    node4=$(echo "$nodes_with_labels" | grep 'node4' | awk '{print $1}')
    kubectl label node $node4 topology.kubernetes.io/zone=us-south-1 --overwrite
    echo "kubectl label node $node4 topology.kubernetes.io/zone=us-south-1 --overwrite"
fi

bash ${repo_dir}/install_istio.sh

kubectl apply -f https://raw.githubusercontent.com/istio/istio/release-1.23/samples/addons/jaeger.yaml

helm upgrade onlineboutique oci://us-docker.pkg.dev/online-boutique-ci/charts/onlineboutique \
    --install

kubectl delete deploy loadgenerator adservice

kubectl apply -f gw_vs_dr.yaml

kubectl apply -f sslateingress.yaml

dupe_exclude=""
/users/gangmuk/projects/SLATE/kube-scripts/dupe-deploys/dupedeploy -deployments=${dupe_exclude} -exclude -regions=${regions}

# swtich image from google official one to ours
/users/gangmuk/projects/SLATE/kube-scripts/dupe-deploys/dupedeploy -justswitchimage -deployments= -exclude

kubectl apply -f ${repo_dir}/proxy_config.yaml
kubectl apply -f ${repo_dir}/wasmplugins.yaml
kubectl apply -f ${repo_dir}/slate-controller.yaml


# exclude the frontend service. In this app, fake-ingress
vs_match_services="sslateingress,slate-controller"
/users/gangmuk/projects/SLATE/kube-scripts/virtualservice-headermatch/vs-headermatch -services=${vs_match_services} -exclude -regions=${regions} &&

bash ${repo_dir}/install_metric_server.sh

# /users/gangmuk/projects/SLATE/wasm-plugins/slate-plugin/slate_service_envoyfilter.yaml needs to be done too
kubectl apply -f /users/gangmuk/projects/SLATE/wasm-plugins/slate-plugin/slate_service_envoyfilter.yaml

update_grace_period

python /users/gangmuk/projects/slate-benchmark/setup_script/scale-replicas.py 4

python /users/gangmuk/projects/slate-benchmark/setup_script/scale-igw.py

python /users/gangmuk/projects/slate-benchmark/setup_script/update_rolling_update.py

if [ $num_regions -ge 4 ]; then
    node5=$(echo "$nodes_with_labels" | grep 'node5' | awk '{print $1}')
    node6=$(echo "$nodes_with_labels" | grep 'node6' | awk '{print $1}')
    python /users/gangmuk/projects/slate-benchmark/setup_script/update-nodeselector.py istio-ingressgateway istio-system $node5
    python /users/gangmuk/projects/slate-benchmark/setup_script/update-nodeselector.py slate-controller default $node6
fi

bash update_ulimit.sh

# change ingress gateway nodeselector, slate controller nodeselector
# scale up replicas of everything except slate-controller
# set filesystem limits on every node
