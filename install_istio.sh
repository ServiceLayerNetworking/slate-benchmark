#curl -L https://istio.io/downloadIstio | sh - &&
curl -L https://istio.io/downloadIstio | ISTIO_VERSION=1.20.3 TARGET_ARCH=x86_64 sh -

cd istio-1.20.3 &&

export PATH=$PWD/bin:$PATH &&

istioctl install &&

kubectl label namespace default istio-injection=enabled --overwrite

#kubectl rollout restart deploy
