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

kubectl apply -f kubernetes.yaml &&
echo "kubectl apply -f kubernetes.yaml"

dupe_services="frontend,a,b,c"
/users/gangmuk/projects/SLATE/kube-scripts/dupe-deploys/dupedeploy -deployments=${dupe_services} -regions=${regions} &&
echo "dupedeploy -deployments=${dupe_services} -regions=${regions}"

read -p "Do you want to install istio? Enter 'y', if yes: " inp
if [ $inp == 'y' ]; then
    bash ${repo_dir}/install_istio.sh &&
    echo "bash ${repo_dir}/install_istio.sh"
fi

kubectl apply -f gw_vs_dr.yaml &&
echo "kubectl apply -f gw_vs_dr.yaml"

kubectl apply -f ${repo_dir}/proxy_config.yaml &&
echo "kubectl apply -f ${repo_dir}/proxy_config.yaml"

kubectl apply -f ${repo_dir}/wasmplugins.yaml &&
echo "kubectl apply -f ${repo_dir}/wasmplugins.yaml"

kubectl apply -f ${repo_dir}/slate-controller.yaml &&
echo "kubectl apply -f ${repo_dir}/slate-controller.yaml"


bash ${repo_dir}/install_metric_server.sh &&
echo "bash ${repo_dir}/install_metric_server.sh"


# exclude the frontend service. In this app, fake-ingress
vs_match_services="a,b,c"
/users/gangmuk/projects/SLATE/kube-scripts/virtualservice-headermatch/vs-headermatch -services=${vs_match_services} -regions=${regions} &&
echo "vs-headermatch -services=${vs_match_services} -regions=${regions}"

update_grace_period
echo "update_grace_period"

