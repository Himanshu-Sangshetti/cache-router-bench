#!/bin/bash
# REC 3 · the heal: identical workload through the llm-d EPP.
set -e; cd "$(dirname "$0")"; source ./lib.sh; need_ip
rssh 'bash -s' <<'REMOTE'
export KUBECONFIG=/etc/rancher/k3s/k3s.yaml
NS="llm-d-precise-prefix-cache-routing"
IP=$(kubectl get service -n $NS -o name | grep epp | head -1 | xargs -I{} kubectl get {} -n $NS -o jsonpath='{.spec.clusterIP}')
MODEL=$(kubectl get deploy -n $NS -o yaml | grep -om1 'meta-llama/[^" ]*\|Qwen/[^" ]*' | head -1)
echo "=== REC 3 · the llm-d router (cache-aware) · $IP ==="
python3 ~/tenants.py "$IP:8000" "$MODEL" 3 2>/dev/null || python3 ~/tenants.py "$IP" "$MODEL" 3
echo
echo "=== the GA resource, on camera ==="
kubectl get inferencepool -n $NS
kubectl get pods -n $NS -o wide | head -8
REMOTE
