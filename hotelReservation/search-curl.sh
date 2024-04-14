#!/bin/bash
set -x
# time curl -v "http://node1.adi.istio-pg0.clemson.cloudlab.us:32433/hotels?inDate=2015-04-01&outDate=2015-04-02&lat=38&lon=-122"
time curl -v -H "x-slate-destination: west" "http://node1.adi.istio-pg0.clemson.cloudlab.us:32433/hotels?inDate=2015-04-01&outDate=2015-04-02&lat=38&lon=-122"

