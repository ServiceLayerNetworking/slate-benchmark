kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml

# Name of the metrics-server deployment
DEPLOYMENT_NAME="metrics-server"

# Namespace where metrics-server is deployed
NAMESPACE="kube-system"

# Check if metrics-server deployment exists
if ! kubectl get deployment "$DEPLOYMENT_NAME" -n "$NAMESPACE" &> /dev/null; then
    echo "Metrics-server deployment not found in namespace $NAMESPACE"
    exit 1
fi

# Patching the deployment
kubectl patch deployment "$DEPLOYMENT_NAME" -n "$NAMESPACE" --type='json' -p='[
    {
        "op": "add",
        "path": "/spec/template/spec/containers/0/args/-",
        "value": "--kubelet-insecure-tls"
    }
]'
#kubectl patch deployment "$DEPLOYMENT_NAME" -n "$NAMESPACE" --type='json' -p='[
#    {
#        "op": "add",
#        "path": "/spec/template/spec/containers/0/args/-",
#        "value": "--kubelet-insecure-tls"
#    },
#    {
#        "op": "replace",
#        "path": "/spec/template/spec/containers/0/args/4",
#        "value": "--metric-resolution=10s"
#    }
#]'

# Checking if the patch was successful
if [ $? -eq 0 ]; then
    echo "Successfully patched metrics-server with --kubelet-insecure-tls argument."
else
    echo "Failed to patch metrics-server deployment."
    exit 1
fi

