# Toy microservice application to benchmark slate-benchmark

# Metrics-microservice-app
#### Usage

#### Topology

#### metrics-handler

#### metircs-processing

---

## Matmul-app
usage: `curl ...`

header
- row: the length of row
- col: the length of column

#### Topology
frontend -> matmul-compute



#### frontend service
It is go server which receives user request and simply forwards to the matmul-compute service.

#### matmul-compute service
It is python server which initializes a new matrix given the size and do matrix multiplication.

