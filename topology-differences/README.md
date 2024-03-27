# Metrics Microservice App

Run `./build-and-push.sh` from metrics-* to push images.

`kubectl apply -f custom-prom.yaml` to deploy prometheus.

`kubectl apply -f k8sconfig.yaml` to deploy app containers.

`GET /start` on metrics-handle to trigger the call to metrics-processor.

To access from outside the cluster, either make the metrics-handle service a NodePort service or install Istio and set up config correctly with IngressGateway.
