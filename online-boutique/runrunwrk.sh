set -x
./togglewasm false
kubectl rollout restart deploy
sleep 180
python run_wrk.py 20 9-9-bg20-nolimit-nojumping
./togglewasm true
kubectl rollout restart deploy
sleep 180
python run_wrk.py 20 9-9-bg20-nolimit-jumping
