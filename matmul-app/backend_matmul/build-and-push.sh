#!/bin/bash

docker build -t gangmuk/matmul-compute:latest .
docker push gangmuk/matmul-compute:latest
