# Setup Guide — SentinelOps Cloud

## Prerequisites

- k3s cluster (single node OK)
- Docker installed
- kubectl configured
- Prometheus, Grafana, Loki running in `monitoring` namespace
- LocalStack running on `localhost:4566` (optional, for AWS emulation)

## 1. Build and deploy demo-app

cd services/demo-app
docker build -t demo-app:v0.1.0 .
docker save demo-app:v0.1.0 | sudo k3s ctr images import -
cd ../..
kubectl apply -f platform/kind/demo-app.yaml
kubectl get pods -l app=demo-app