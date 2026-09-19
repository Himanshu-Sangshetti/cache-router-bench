#!/bin/bash
# THE SETUP TOUR · run this on camera BEFORE the demos.
set -e; cd "$(dirname "$0")"; source ./lib.sh; need_ip
rssh 'bash -s' <<'REMOTE'
export KUBECONFIG=/etc/rancher/k3s/k3s.yaml
NS=llm-d-precise-prefix-cache-routing
p(){ echo; echo "\$ $*"; "$@"; sleep 1; }
echo "=============================================================="
echo " THE SETUP · real Kubernetes · real llm-d · real vLLM"
echo "=============================================================="
p kubectl get nodes -o wide
p kubectl get pods -n $NS -o wide
p helm list -n $NS
p kubectl get inferencepool -n $NS
p kubectl get svc -n $NS
echo
echo "\$ # the vLLM pods run with the exact flags from the talk:"
kubectl get deploy -n $NS precise-prefix-cache-routing-cpu-vllm-decode \
  -o jsonpath='{.spec.template.spec.containers[0].args}' | tr ',' '\n' | grep -E "kv-events|block-size|serve|Qwen" | sed 's/^/    /'
echo
echo "  components: EPP = llm-d router (the phone book) · 2x vLLM pods (private caches)"
echo "  standard:   InferencePool (Gateway API Inference Extension, GA v1)"
REMOTE
