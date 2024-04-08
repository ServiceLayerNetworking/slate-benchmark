prefix=$1

python send_w200s350c50e50.py ${prefix}-t1 # at t=0 for 120s
echo "START t=0: python run_wrk.py ${prefix}-t1 # at t=0 for 120s"
python send_east_150rps.py ${prefix}-t2 # at t=10 for 110s
echo "START t=10: python send_east_150rps.py ${prefix}-t2 # at t=10 for 110s"

sleep 10
kill -9 $(ps -ef | grep wrk | grep ${prefix}-t2 | awk '{print $2}') # at t=30
echo "kill -9 $(ps -ef | grep wrk | grep ${prefix}-t2 | awk '{print $2}')"
python send_west_150rps.py ${prefix}-t3 # at t=30 for 90s
echo "START t=40: python send_west_150rps.py ${prefix}-t3 # at t=40 for 80s"

sleep 90
kill -9 $(ps -ef | grep wrk | grep ${prefix}-t1 | awk '{print $2}') # at t=30
kill -9 $(ps -ef | grep wrk | grep ${prefix}-t3 | awk '{print $2}') # at t=30