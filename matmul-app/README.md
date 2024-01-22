# Matmul

GET and POST are currently doing the exact same thing.
Two methods are used to distinguish compute heavy and compute light.

**GET**
GET should be light weight matmul which means rows and columns should be small number. 
Use rows=2, columns=2

**POST**
POST should be light weight matmul which means rows and columns should be large number.
Use rows=100, columns=100

### curl
#### GET
curl -v -H "x-slate-destination: west" http://node2.gangmuk-185120.istio-pg0.clemson.cloudlab.us:30763/compute\?row\=2\&column\=2

#### POST
curl -v -X POST -H "x-slate-destination: west" http://node2.gangmuk-185120.istio-pg0.clemson.cloudlab.us:30763/compute\?row\=100\&column\=100
