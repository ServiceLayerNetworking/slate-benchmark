#docker build -t gangmuk/metrics-fake-ingress:latest .
#docker push gangmuk/metrics-fake-ingress:latest
# spread-frontend
docker build -t ghcr.io/adiprerepa/spread-handler:latest .
docker push ghcr.io/adiprerepa/spread-handler:latest

docker build -t ghcr.io/adiprerepa/spread-processor:latest .
docker push ghcr.io/adiprerepa/spread-processor:latest


docker build -t ghcr.io/adiprerepa/spread-db:latest .
docker push ghcr.io/adiprerepa/spread-db:latest

docker build -t ghcr.io/adiprerepa/spread-frontend:latest .
docker push ghcr.io/adiprerepa/spread-frontend:latest
