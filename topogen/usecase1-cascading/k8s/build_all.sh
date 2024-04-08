
app_dir="/users/gangmuk/projects/slate-benchmark/topogen/usecase1-whichcluster/k8s/222mb"
# app_dir="/users/gangmuk/projects/slate-benchmark/topogen/usecase1-whichcluster/k8s/112mb"

cd ${app_dir}/frontend
./build-and-push.sh &
echo "frontend done"

cd ${app_dir}/a
./build-and-push.sh &
echo "a done"

cd ${app_dir}/b
./build-and-push.sh &
echo "b done"

cd ${app_dir}/c
./build-and-push.sh &
echo "c done"

cd ${app_dir}/d
./build-and-push.sh
echo "d done"