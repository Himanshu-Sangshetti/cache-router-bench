#!/bin/bash
# REC 2 · the scatter: same pods behind a stock cache-blind Service.
set -e; cd "$(dirname "$0")"; source ./lib.sh; need_ip
rssh 'bash -s' <<'REMOTE'
export KUBECONFIG=/etc/rancher/k3s/k3s.yaml
NS="llm-d-precise-prefix-cache-routing"
DEP=$(kubectl get deploy -n $NS -o name | grep -vi -e epp -e render | head -1 | cut -d/ -f2)
kubectl get svc blind -n $NS >/dev/null 2>&1 || kubectl expose deploy "$DEP" -n $NS --name blind --port 8000 --target-port 8000
BIP=$(kubectl get svc blind -n $NS -o jsonpath='{.spec.clusterIP}')
MODEL=$(kubectl get deploy -n $NS -o yaml | grep -om1 'meta-llama/[^" ]*\|Qwen/[^" ]*' | head -1)
echo "=== REC 2 · stock Service (round-robin, cache-blind) · $BIP ==="
python3 ~/tenants.py "$BIP:8000" "$MODEL" 3
REMOTE
