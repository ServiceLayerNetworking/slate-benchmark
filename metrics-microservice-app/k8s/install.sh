echo "It assumes that k8s is clean without anything installed or configured"

bash ../../label_node.sh &&
echo "bash ../../label_node.sh"

kubectl apply -f k8sconfig.yaml &&
echo "kubectl apply -f k8sconfig.yaml"

bahs ./duplicate.sh &&
echo "duplicate.sh"

read -p "Do you want to install istio? Enter 'y', if yes: " inp
if [ $inp == 'y' ]; then
    bash ../../install_istio.sh &&
    echo "bash ../../install_istio.sh"
fi

kubectl apply -f gw_vs_dr.yaml &&
echo "kubectl apply -f gw_vs_dr.yaml"

kubectl apply -f proxy_config.yaml &&
echo "kubectl apply -f proxy_config.yaml"

kubectl apply -f ../../wasmplugins.yaml &&
echo "kubectl apply -f ../../wasmplugins.yaml"

kubectl apply -f ../../slate-controller.yaml &&
echo "kubectl apply -f ../../slate-controller.yaml"

bash ./vs_match.sh &&
echo "vs_match.sh"

kubectl rollout restart deploy &&
echo "kubectl rollout restart deploy"
