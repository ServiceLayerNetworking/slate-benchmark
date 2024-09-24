python run_wrk.py 20 profile-9-10-bg20
kubectl rollout restart deploy
python run_wrk.py 40 profile-9-10-bg40
kubectl rollout restart deploy
python run_wrk.py 60 profile-9-10-bg60
