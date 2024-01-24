

distribution=exp
thread=20
connection=20
duration=30
RPS=30
req_type=get # post
cluster=west
server_ip="http://node1.gangmuk-186812.istio-pg0.utah.cloudlab.us:30669"

./wrk -D ${distribution} -t${thread} -c${connection} -d${duration} -L -S -s ./${cluster}_${req_type}.lua ${server_ip} -R${RPS}
# ./hit -d 10 -rps 2 -l "google.log" -url "http://www.google.com"
