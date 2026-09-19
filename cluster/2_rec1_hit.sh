#!/bin/bash
# REC 1 · lever 1 on the real engine: cold -> hit, then the engine's own counters.
set -e; cd "$(dirname "$0")"; source ./lib.sh; need_ip
rssh 'bash -s' <<'REMOTE'
export KUBECONFIG=/etc/rancher/k3s/k3s.yaml
NS="llm-d-precise-prefix-cache-routing"
IP=$(kubectl get service -n $NS -o name | grep epp | head -1 | xargs -I{} kubectl get {} -n $NS -o jsonpath='{.spec.clusterIP}')
MODEL=$(kubectl get deploy -n $NS -o yaml | grep -om1 'meta-llama/[^" ]*\|Qwen/[^" ]*' | head -1)
echo "=== REC 1 · endpoint $IP · model $MODEL ==="
python3 ~/hit.py "$IP:8000" "$MODEL" 2>/dev/null || python3 ~/hit.py "$IP" "$MODEL"
echo
echo "=== the engine's own receipt ==="
POD=$(kubectl get pods -n $NS -l 'llm-d.ai/guide' -o name | head -1)
kubectl exec -n $NS "$POD" -- curl -s localhost:8000/metrics 2>/dev/null | grep -E "prefix_cache_(hits|queries)" | grep -v "^#"
REMOTE
