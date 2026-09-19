#!/bin/bash
# Install the REAL stack on the box: k3s + GAIE CRDs + llm-d router (EPP) +
# 2x vLLM model servers (official CPU variant) + render service.
# Usage: HF_TOKEN=hf_xxx ./1_bootstrap_stack.sh          (~15-25 min, mostly pulls)
set -e; cd "$(dirname "$0")"; source ./lib.sh; need_ip
HF_TOKEN="${HF_TOKEN:-hf_dummy_not_needed_for_ungated_model}"
echo ">>> bootstrapping on $IP"
rssh "HF_TOKEN='$HF_TOKEN' bash -s" <<'REMOTE'
set -e
command -v kubectl >/dev/null || curl -sfL https://get.k3s.io | sh -
sudo chmod 644 /etc/rancher/k3s/k3s.yaml
export KUBECONFIG=/etc/rancher/k3s/k3s.yaml
grep -q KUBECONFIG ~/.bashrc || echo 'export KUBECONFIG=/etc/rancher/k3s/k3s.yaml' >> ~/.bashrc
command -v helm >/dev/null || curl -s https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
[ -d ~/llm-d ] || git clone --depth 1 https://github.com/llm-d/llm-d.git ~/llm-d
cd ~/llm-d
# swap the gated CI model for an ungated one, everywhere in this guide
grep -rl 'meta-llama/Llama-3.2-3B-Instruct' guides/precise-prefix-cache-routing \
  | xargs sed -i 's|meta-llama/Llama-3.2-3B-Instruct|Qwen/Qwen2.5-3B-Instruct|g' || true
export REPO_ROOT=$PWD
source ${REPO_ROOT}/guides/env.sh
export GUIDE_NAME="precise-prefix-cache-routing"
export NAMESPACE="llm-d-${GUIDE_NAME}"
kubectl apply -f https://github.com/kubernetes-sigs/gateway-api-inference-extension/${GAIE_URL}/v1-manifests.yaml
kubectl create namespace ${NAMESPACE} --dry-run=client -o yaml | kubectl apply -f -
kubectl create secret generic llm-d-hf-token --from-literal="HF_TOKEN=${HF_TOKEN}" \
  --namespace "${NAMESPACE}" --dry-run=client -o yaml | kubectl apply -f -
helm list -n ${NAMESPACE} | grep -q ${GUIDE_NAME} || helm install ${GUIDE_NAME} \
  ${ROUTER_STANDALONE_CHART} \
  -f ${REPO_ROOT}/guides/recipes/router/base.values.yaml \
  -f ${REPO_ROOT}/guides/${GUIDE_NAME}/router/${GUIDE_NAME}.values.yaml \
  -n ${NAMESPACE} --version ${ROUTER_CHART_VERSION}
kubectl apply -n ${NAMESPACE} -k ${REPO_ROOT}/guides/${GUIDE_NAME}/modelserver/cpu/vllm/
echo "waiting for a model server to be Ready (image + weights pull, be patient)..."
kubectl wait -n ${NAMESPACE} --for=condition=Ready pod \
  -l 'llm-d.ai/guide' --timeout=30m || kubectl get pods -n ${NAMESPACE}
kubectl apply -n ${NAMESPACE} -k ${REPO_ROOT}/guides/${GUIDE_NAME}/render/
kubectl wait -n ${NAMESPACE} --for=condition=Ready pod --all --timeout=30m || true
echo; echo "=== STACK UP ==="; kubectl get pods -n ${NAMESPACE} -o wide
kubectl get inferencepool -n ${NAMESPACE} 2>/dev/null || true
REMOTE
rscp workloads/*.py ubuntu@"$IP":~/
echo ">>> done. next: ./2_rec1_hit.sh"
