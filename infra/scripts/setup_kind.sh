#!/usr/bin/env bash
# ==============================================================================
# KinD Local Cluster Setup with gVisor (runsc) Emulation and containerd config
# ==============================================================================
set -euo pipefail

CLUSTER_NAME="${CLUSTER_NAME:-aegis-kind-cluster}"
KIND_CONFIG_FILE="/tmp/kind-gvisor-config.yaml"

echo "==> Configuring KinD cluster '${CLUSTER_NAME}' with gVisor support..."

cat <<EOF > "${KIND_CONFIG_FILE}"
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
nodes:
- role: control-plane
  extraPortMappings:
  - containerPort: 80
    hostPort: 8080
    protocol: TCP
  - containerPort: 443
    hostPort: 8443
    protocol: TCP
  - containerPort: 8000
    hostPort: 8000
    protocol: TCP
  - containerPort: 8001
    hostPort: 8001
    protocol: TCP
- role: worker
  extraMounts:
  - hostPath: /dev/null
    containerPath: /dev/null
EOF

if kind get clusters | grep -q "^${CLUSTER_NAME}$"; then
  echo "KinD cluster '${CLUSTER_NAME}' already exists. Reusing existing cluster."
else
  echo "Creating KinD cluster '${CLUSTER_NAME}'..."
  kind create cluster --name "${CLUSTER_NAME}" --config "${KIND_CONFIG_FILE}"
fi

echo "==> Configuring worker node with containerd gVisor runsc runtime..."
WORKER_NODE="${CLUSTER_NAME}-worker"

# Check if worker node container exists
if docker ps --format '{{.Names}}' | grep -q "${WORKER_NODE}"; then
  echo "Injecting gVisor runsc containerd configuration on ${WORKER_NODE}..."
  docker exec "${WORKER_NODE}" bash -c "
    if ! command -v runsc &> /dev/null; then
      echo 'Installing runsc gVisor binary...'
      ARCH=\$(uname -m)
      URL=https://storage.googleapis.com/gvisor/releases/release/latest/\${ARCH}
      curl -fsSL \${URL}/runsc -o /usr/local/bin/runsc || true
      chmod a+rx /usr/local/bin/runsc || true
    fi
    mkdir -p /etc/containerd/conf.d
    cat <<'CRICFG' > /etc/containerd/conf.d/gvisor.toml
[plugins.\"io.containerd.grpc.v1.cri\".containerd.runtimes.runsc]
  runtime_type = \"io.containerd.runsc.v1\"
CRICFG
    systemctl restart containerd || true
  " || true
fi

echo "==> Applying Kubernetes RuntimeClass for gVisor..."
kubectl apply -f - <<'EOF' || true
apiVersion: node.k8s.io/v1
kind: RuntimeClass
metadata:
  name: gvisor
handler: runsc
EOF

echo "==> KinD cluster '${CLUSTER_NAME}' ready."
