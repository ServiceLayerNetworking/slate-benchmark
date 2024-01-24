# Toy microservice application to benchmark slate-benchmark
---
## required setup
label node
```
node1=$1
node2=$2
kubectl label node $node1 topology.kubernetes.io/zone=us-west-1
kubectl label node $node2 topology.kubernetes.io/zone=us-east-1
```


`k apply -f k8sconfig.yaml`
- deployment of application
- services for deployment

install istioctl and istio

`k apply -f matmul_dr_vs_gw.yaml`
- gateway, gateway virtualservice, frontend destination rule, jaeger proxyconfig

`k apply -f wasmplugin.yaml`

`k appl y-f slate-controller.yaml`

`dupedeploy` except for slate-controller and consul

`vs-headermatch` except for the frontend deployment


- Gateway
  - requests from `hosts: "*"` to http port 80.
  - istio-ingressgateway service should have http port 80
- VirtualService for matmul-gateway
  - It needs an additional field `gateways: matmul-gateway`. Then the gateway request will
  - If headers match `x-slate-destination: east`, routes the request to `matmul-frontend` service's `subset: east` to port 8000 (check matmul-frontend svc has 8000 port)
- DestinationRule for frontend service
  - For requests from `host: matmul-frontend`, subset `name: east` label it with `region: us-east-1`
  - What does it do?
- **how does matmul-compute receive request?**
 
- **port in gateway virtualservice, http port in matmul-frontend svc should match**

- ProxyConfig to set proxy environment variable
  - `us-east-1` for proxy which has label `region: us-east-1`
  - `us-west-1` for proxy which has label `region: us-west-1`
- ConfigMap for shared span

---
## Metrics-microservice-app
#### Usage

#### Topology

#### metrics-handler

#### metircs-processing

---

## Matmul-app
usage: `curl -v -X GET -H "x-slate-destination: west" node1_dns:nodeport_of_ingressgateway_svc/compute\?row\=2\&column\=2`
usage: `curl -v -X POST -H "x-slate-destination: west" node1_dns:nodeport_of_ingressgateway_svc/compute\?row\=2\&column\=2`

endpoint: `compute`
header
- `row`: the length of row
- `column`: the length of column

#### Topology
frontend -> matmul-compute

#### frontend service
It is go server which receives user request and simply forwards to the matmul-compute service.

#### matmul-compute service
It is python server which initializes a new matrix given the size and do matrix multiplication.

