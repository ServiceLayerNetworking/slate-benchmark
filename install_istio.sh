curl -L https://istio.io/downloadIstio | sh - &&

cd istio-1.20.3 &&

export PATH=$PWD/bin:$PATH &&

istioctl install &&

kubectl label namespace default istio-injection=enabled --overwrite &&

#kubectl rollout restart deploy
